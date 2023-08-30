# Binance Arbitrage Bot

This bot is designed to detect arbitrage opportunities in the Binance exchange using triangular arbitrage. It checks for triangular trading pairs and identifies potential arbitrage opportunities between them. If a profitable trade is detected, the bot will execute the necessary orders to exploit the opportunity.

## Prerequisites

- **Python 3.6+**: Ensure you have Python 3.6 or newer installed.

- **Required Libraries**: Install the required Python libraries:
    ```bash
    pip install requests aiohttp python-binance
    ```

## Configuration

### API Credentials:
Replace the placeholders `api_key` and `api_secret` in the code with your Binance API credentials:
    - `api_key` = "YOUR_API_KEY_HERE"
    - `api_secret` = "YOUR_API_SECRET_HERE"

### Trading Parameters:
- You can adjust parameters like `maker_fee`, `taker_fee`, and `my_usdt_amount` in the `find_arbitrage_opportunities` function to match your trading preferences and fee structure.

## Running the Bot

To run the bot, execute the following command:

```bash
python main.py
 ```

### NOTES:
- Please be aware that trading cryptocurrencies is risky, and you should only trade with funds you can afford to lose.
- This bot is provided for educational purposes only. Make sure to test thoroughly in a sandbox or with small amounts before deploying with larger sums.
