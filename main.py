import requests
import json

from binance.client import Client, AsyncClient
import threading
import logging
import asyncio
import aiohttp
import time

#mainnet
api_key=""
api_secret=""

client = Client(api_key, api_secret)
asyncClient = AsyncClient(api_key, api_secret)


url_test = "https://testnet.binance.vision/"
url_main="https://api.binance.com/"

def get_all_symbols():
    allsymbols = []

    r = requests.get(url="https://api.binance.com/api/v3/exchangeInfo")
    for k in r.json()['symbols']:
        if k['status'] == 'TRADING':
            allsymbols.append(k['symbol'].lower())
    return allsymbols

def find_triangular_pairs(symbols):
    triangular_pairs = []
    seen_pairs = set()

    # All pairs involving USDT
    usdt_pairs = [s for s in symbols if s.startswith("usdt") or s.endswith("usdt")]

    for pair in usdt_pairs:
        first_currency, second_currency = pair.split("usdt")
        first_currency, second_currency = (second_currency, first_currency) if first_currency == "" else (first_currency, second_currency)

        # Looking for pairs that involve the first currency and don't involve USDT
        first_currency_pairs = [s for s in symbols if (s.startswith(first_currency) or s.endswith(first_currency)) and "usdt" not in s]

        for first_pair in first_currency_pairs:
            if first_pair.startswith(first_currency):
                intermediate_currency = first_pair.replace(first_currency, "", 1)
            else:
                intermediate_currency = first_pair.replace(first_currency, "")

            # Check if a trade from the intermediate_currency back to USDT exists and if the triangular pair hasn't been seen yet.
            third_pair = f"{intermediate_currency}usdt"
            if third_pair in symbols and frozenset([pair, first_pair, third_pair]) not in seen_pairs:
                triangular_pairs.append([pair, first_pair, third_pair])
                seen_pairs.add(frozenset([pair, first_pair, third_pair]))

        # Similarly, looking for pairs that involve the second currency (since trades can go both ways) and don't involve USDT
        second_currency_pairs = [s for s in symbols if (s.startswith(second_currency) or s.endswith(second_currency)) and "usdt" not in s]

        for second_pair in second_currency_pairs:
            if second_pair.startswith(second_currency):
                intermediate_currency = second_pair.replace(second_currency, "", 1)
            else:
                intermediate_currency = second_pair.replace(second_currency, "")

            # Check if a trade from the intermediate_currency back to USDT exists and if the triangular pair hasn't been seen yet.
            third_pair = f"{intermediate_currency}usdt"
            if third_pair in symbols and frozenset([pair, second_pair, third_pair]) not in seen_pairs:
                triangular_pairs.append([pair, second_pair, third_pair])
                seen_pairs.add(frozenset([pair, second_pair, third_pair]))

    return triangular_pairs


async def get_order_book(symbol, limit=100):
    BASE_URL = 'https://api.binance.com/api/v3/depth'
    params = {
        'symbol': symbol,
        'limit': limit
    }
    response = requests.get(BASE_URL, params=params)
    data = response.json()
    return data

async def check_liquidity(symbol, amount, price, side):
    order_book = await get_order_book(symbol, 100)
    if side == 'buy':
        orders = order_book['asks']
    else:
        orders = order_book['bids']

    cumulative_volume = 0.0
    for order in orders:
        order_price, volume = float(order[0]), float(order[1])
        if side == 'buy' and order_price <= price:
            cumulative_volume += volume
        elif side == 'sell' and order_price >= price:
            cumulative_volume += volume
        else:
            break

        if cumulative_volume >= amount:
            return True  # There's enough liquidity

    return False

async def get_price_of_symbol(symbol):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://www.binance.com/api/v3/ticker/price?symbol={symbol.upper()}") as response:
            data = await response.json()
            return float(data['price'])
import re
async def place_order(symbol, side, price, timeout=120):
    #waits for 2 mins for trade
    exchange_info = client.get_exchange_info()
    precision = get_quote_precision(symbol.upper(), exchange_info)
    get_asset_qty = client.get_asset_balance(symbol.replace('usdt', '').upper())
    print(get_asset_qty)
    print(precision, f"for {symbol.upper()}")

    if re.match(r"[-+]?\d*\.?\d+e[-+]?\d+", str(price)): #TODO CHANGE
        price = "{:.8f}".format(price)
        quantity = round(float(get_asset_qty['free'])/float(price), precision)
    else:
        price = round(price, precision)
        quantity = round(11 / float(price) * 0.9, precision)
    print(f"Rounded price for {symbol}: {price}")
    print(f"Rounded Quantity for {symbol}: {quantity}")


    order = await asyncClient.create_order(symbol=symbol.upper(), side=side, type="LIMIT", quantity=quantity, price=price, timeInForce='GTC')
    print(f"Placed {side} order for {symbol} at price {price}")

    start_time = time.time()
    while (time.time() - start_time) < timeout:
        order_status = await asyncClient.get_order(symbol=symbol.upper(), orderId=order["orderId"])
        if order_status["status"] == "FILLED":
            print(f"Order {order['orderId']} for {symbol} has been fulfilled.")
            return True
        else:
            print(f"Order {order['orderId']} for {symbol} is not yet fulfilled. Status: {order_status['status']}")
        await asyncio.sleep(2)


    print(f"Order {order['orderId']} for {symbol} was not fulfilled in time.")
    # cancel_order = await asyncClient.cancel_order(symbol=symbol.upper(), orderId=order["orderId"])
    # print(cancel_order, "ORDER CANCELED")
    return False


def process_buy_or_sell(listofstring):
    order_type = []
    get_another_symbol = listofstring[0].strip('usdt') #BTC
    get_middle_symbol = listofstring[1].strip(get_another_symbol) #eth
    if listofstring[0].startswith('usdt'):
        order_type.append("SELL")
    else:
        order_type.append("BUY")
    if listofstring[1].startswith(get_another_symbol):
        order_type.append("SELL")
    else:
        order_type.append("BUY")
    if listofstring[2].startswith('usdt'):
        order_type.append("BUY")
    else:
        order_type.append("SELL")
    return order_type


def get_quote_precision(pair, exchange_info):
    for symbol_info in exchange_info["symbols"]:
        if symbol_info["symbol"] == pair:
            lot_size = symbol_info["filters"][1]
            step_size = lot_size["stepSize"]

            # Check if stepSize is a whole number
            if '.' not in step_size or step_size.endswith('.00000000'):
                return 0

            after_decimal = step_size.split('.')[-1]

            # Count number of zeroes until the first non-zero character
            count = 0
            for char in after_decimal:
                if char == '0':
                    count += 1
                else:
                    break

            return count
    return None
async def find_arbitrage_opportunities(triangular_pairs, maker_fee=0.001, taker_fee=0.001, my_usdt_amount=100):
    opportunities = []


    for pairs in triangular_pairs:
        order_types = process_buy_or_sell(pairs)
        price_A = await get_price_of_symbol(pairs[0])
        price_B = await get_price_of_symbol(pairs[1])
        price_C = await get_price_of_symbol(pairs[2])

        print(f"Prices for {pairs[0]}, {pairs[1]}, {pairs[2]}: {price_A}, {price_B}, {price_C}")



        total_first_trade = my_usdt_amount / price_A * (1 - (0.1 / 100))  # AMOUNT IN BTC after fee
        total_second_trade = total_first_trade / price_B * (1 - (0.1 / 100)) #AMount IN ETH after fee
        total_third_trade = total_second_trade*price_C*(1 - (0.1 / 100))

        calculate_percentage = (total_third_trade-my_usdt_amount)/100

        has_liquidity_A = await check_liquidity(pairs[0].upper(), my_usdt_amount / price_A, price_A, order_types[0].lower())
        has_liquidity_B = await check_liquidity(pairs[1].upper(), total_first_trade, price_B, order_types[1].lower())
        has_liquidity_C = await check_liquidity(pairs[2].upper(), total_second_trade, price_C, order_types[2].lower())


        if calculate_percentage>0.001 and calculate_percentage<0.5:
            if has_liquidity_A and has_liquidity_B and has_liquidity_C:
                print(calculate_percentage)
                print("trade successful")
                opportunities.append(
                    {"pairs": pairs, "winrate": calculate_percentage, "prices": [price_A, price_B, price_C],
                     "order_types": order_types})
                success_A = await place_order(pairs[0], order_types[0], price_A)
                if success_A:
                    success_B = await place_order(pairs[1], order_types[1], price_B)
                    if success_B:
                        await place_order(pairs[2], order_types[2], price_C)
                        print('all orders Successfull')
            else:
                print("no liquidity")
                pass

        else:
            print("trade not successful")

    print(opportunities)


loop = asyncio.get_event_loop()
while True:
    try:
        loop.run_until_complete(find_arbitrage_opportunities(find_triangular_pairs(get_all_symbols())))
    finally:
        loop.close()
        loop = asyncio.new_event_loop()