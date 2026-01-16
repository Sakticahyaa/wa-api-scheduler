#!/usr/bin/env python3
"""
Stock Market Notification System for Huawei Band 10
Fetches BTC, SUI, BNB, and XRP prices and sends to Telegram
"""

import os
import sys
import requests
import yfinance as yf
from datetime import datetime


def fetch_crypto_price(symbol, binance_symbol, coingecko_id):
    """Fetch current price and percentage changes for a crypto with multiple API fallbacks"""

    # Try Method 1: Binance API (most reliable, no rate limits)
    try:
        print(f"  [{symbol}] [1/3] Trying Binance API...")

        # Get current price and 24h change
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={binance_symbol}"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            current_price = float(data['lastPrice'])
            change_24h = float(data['priceChangePercent'])

            # Get 1-hour change using klines (candlestick data)
            change_1h = 0.0
            try:
                # Get the last completed 1-hour candle (1 hour ago)
                klines_url = f"https://api.binance.com/api/v3/klines?symbol={binance_symbol}&interval=1h&limit=2"
                klines_response = requests.get(klines_url, timeout=10)

                if klines_response.status_code == 200:
                    klines = klines_response.json()
                    if len(klines) >= 1:
                        # klines format: [open_time, open, high, low, close, ...]
                        # Use the close price of the last completed 1h candle (1 hour ago)
                        price_1h_ago = float(klines[-2][4]) if len(klines) >= 2 else float(klines[-1][1])

                        # Compare with current price (from the ticker data we already have)
                        change_1h = ((current_price - price_1h_ago) / price_1h_ago) * 100
                        print(f"  [{symbol}] 1h change: {change_1h:+.2f}%")
            except Exception as e1h:
                print(f"  [{symbol}] Warning: Could not fetch 1h data: {e1h}")

            print(f"  [{symbol}] Success with Binance! Price: ${current_price:,.2f}, 24h: {change_24h:+.2f}%, 1h: {change_1h:+.2f}%")
            return current_price, change_24h, change_1h
    except Exception as e:
        print(f"  [{symbol}] Binance failed: {e}")

    # Try Method 2: CoinGecko API
    try:
        print(f"  [{symbol}] [2/3] Trying CoinGecko API...")

        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coingecko_id}&vs_currencies=usd&include_24hr_change=true"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            print(f"  [{symbol}] CoinGecko price API returned status {response.status_code}: {response.text[:100]}")

        if response.status_code == 200:
            data = response.json()
            if coingecko_id in data:
                current_price = data[coingecko_id]['usd']
                change_24h = data[coingecko_id]['usd_24h_change']

                # Try to get 1-hour change from market chart
                change_1h = 0.0
                try:
                    # Get last 2 hours of data to calculate 1-hour change
                    import time

                    # Add extra delay for XRP to avoid rate limiting
                    if symbol == "XRP":
                        time.sleep(2)

                    current_timestamp = int(time.time())
                    from_timestamp = current_timestamp - 7200  # 2 hours ago

                    chart_url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}/market_chart/range?vs_currency=usd&from={from_timestamp}&to={current_timestamp}"
                    chart_response = requests.get(chart_url, timeout=10)

                    if chart_response.status_code == 200:
                        chart_data = chart_response.json()
                        if 'prices' in chart_data and len(chart_data['prices']) >= 2:
                            # Get the most recent price (latest)
                            latest_price = chart_data['prices'][-1][1]
                            latest_timestamp = chart_data['prices'][-1][0] / 1000  # Convert to seconds

                            # Find the price closest to exactly 1 hour (3600 seconds) ago
                            target_timestamp = latest_timestamp - 3600
                            closest_idx = 0
                            min_diff = float('inf')

                            for i, (timestamp_ms, price) in enumerate(chart_data['prices']):
                                timestamp = timestamp_ms / 1000
                                diff = abs(timestamp - target_timestamp)
                                if diff < min_diff:
                                    min_diff = diff
                                    closest_idx = i

                            price_1h_ago = chart_data['prices'][closest_idx][1]
                            change_1h = ((latest_price - price_1h_ago) / price_1h_ago) * 100
                            print(f"  [{symbol}] 1h change: {change_1h:+.2f}%")
                        else:
                            print(f"  [{symbol}] Warning: Not enough price data for 1h calculation")
                except Exception as e1h:
                    print(f"  [{symbol}] Warning: Could not fetch 1h data: {e1h}")
                    import traceback
                    traceback.print_exc()

                print(f"  [{symbol}] Success with CoinGecko! Price: ${current_price:,.2f}, 24h: {change_24h:+.2f}%, 1h: {change_1h:+.2f}%")
                return current_price, change_24h, change_1h
    except Exception as e:
        print(f"  [{symbol}] CoinGecko failed: {e}")

    # All methods failed
    print(f"  [{symbol}] ERROR: All API sources failed")
    return None, None, None


def fetch_all_cryptos_batch():
    """Fetch all 4 cryptos in a single batch call to avoid rate limiting"""
    import time
    print("Fetching all crypto prices in batch...")

    try:
        # Single batch call for all 4 cryptos (price + 24h change)
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,sui,binancecoin,ripple&vs_currencies=usd&include_24hr_change=true"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            print(f"  Batch API returned status {response.status_code}: {response.text[:100]}")
            return None

        data = response.json()
        print(f"  Successfully fetched all 4 cryptos in one call")

        # Extract data for each crypto
        results = {}
        for symbol, coin_id in [("BTC", "bitcoin"), ("SUI", "sui"), ("BNB", "binancecoin"), ("XRP", "ripple")]:
            if coin_id in data:
                results[symbol] = {
                    "price": data[coin_id]['usd'],
                    "change_24h": data[coin_id]['usd_24h_change']
                }
            else:
                results[symbol] = None

        return results

    except Exception as e:
        print(f"  Batch fetch failed: {e}")
        return None


def fetch_stock_data():
    """Fetch BTC, SUI, BNB, and XRP prices"""
    import time
    print("Fetching crypto prices...")

    # Try batch fetch first (more efficient, avoids rate limiting)
    batch_data = fetch_all_cryptos_batch()

    if batch_data:
        # Fetch 1-hour data for each crypto with delays
        btc_price = batch_data["BTC"]["price"] if batch_data["BTC"] else None
        btc_24h = batch_data["BTC"]["change_24h"] if batch_data["BTC"] else 0
        btc_1h = 0.0
        if btc_price:
            time.sleep(2)
            btc_1h = fetch_1h_change("BTC", "bitcoin")

        sui_price = batch_data["SUI"]["price"] if batch_data["SUI"] else None
        sui_24h = batch_data["SUI"]["change_24h"] if batch_data["SUI"] else 0
        sui_1h = 0.0
        if sui_price:
            time.sleep(2)
            sui_1h = fetch_1h_change("SUI", "sui")

        bnb_price = batch_data["BNB"]["price"] if batch_data["BNB"] else None
        bnb_24h = batch_data["BNB"]["change_24h"] if batch_data["BNB"] else 0
        bnb_1h = 0.0
        if bnb_price:
            time.sleep(2)
            bnb_1h = fetch_1h_change("BNB", "binancecoin")

        xrp_price = batch_data["XRP"]["price"] if batch_data["XRP"] else None
        xrp_24h = batch_data["XRP"]["change_24h"] if batch_data["XRP"] else 0
        xrp_1h = 0.0
        if xrp_price:
            time.sleep(2)
            xrp_1h = fetch_1h_change("XRP", "ripple")

        return (btc_price, btc_24h, btc_1h), (sui_price, sui_24h, sui_1h), (bnb_price, bnb_24h, bnb_1h), (xrp_price, xrp_24h, xrp_1h)

    # Fallback to individual fetches if batch fails
    print("  Batch fetch failed, trying individual fetches...")

    # Fetch BTC
    print("\n  Fetching BTC...")
    btc_price, btc_24h, btc_1h = fetch_crypto_price("BTC", "BTCUSDT", "bitcoin")
    time.sleep(3)

    # Fetch SUI
    print("\n  Fetching SUI...")
    sui_price, sui_24h, sui_1h = fetch_crypto_price("SUI", "SUIUSDT", "sui")
    time.sleep(3)

    # Fetch BNB
    print("\n  Fetching BNB...")
    bnb_price, bnb_24h, bnb_1h = fetch_crypto_price("BNB", "BNBUSDT", "binancecoin")
    time.sleep(3)

    # Fetch XRP
    print("\n  Fetching XRP...")
    xrp_price, xrp_24h, xrp_1h = fetch_crypto_price("XRP", "XRPUSDT", "ripple")

    return (btc_price, btc_24h, btc_1h), (sui_price, sui_24h, sui_1h), (bnb_price, bnb_24h, bnb_1h), (xrp_price, xrp_24h, xrp_1h)


def fetch_1h_change(symbol, coingecko_id):
    """Fetch only 1-hour change for a specific crypto"""
    try:
        import time
        current_timestamp = int(time.time())
        from_timestamp = current_timestamp - 7200  # 2 hours ago

        chart_url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}/market_chart/range?vs_currency=usd&from={from_timestamp}&to={current_timestamp}"
        chart_response = requests.get(chart_url, timeout=10)

        if chart_response.status_code == 200:
            chart_data = chart_response.json()
            if 'prices' in chart_data and len(chart_data['prices']) >= 2:
                latest_price = chart_data['prices'][-1][1]
                latest_timestamp = chart_data['prices'][-1][0] / 1000

                target_timestamp = latest_timestamp - 3600
                closest_idx = 0
                min_diff = float('inf')

                for i, (timestamp_ms, price) in enumerate(chart_data['prices']):
                    timestamp = timestamp_ms / 1000
                    diff = abs(timestamp - target_timestamp)
                    if diff < min_diff:
                        min_diff = diff
                        closest_idx = i

                price_1h_ago = chart_data['prices'][closest_idx][1]
                change_1h = ((latest_price - price_1h_ago) / price_1h_ago) * 100
                print(f"  [{symbol}] 1h change: {change_1h:+.2f}%")
                return change_1h

    except Exception as e:
        print(f"  [{symbol}] Could not fetch 1h data: {e}")

    return 0.0


def format_message(btc_data, sui_data, bnb_data, xrp_data):
    """Format message for small wearable screen with BTC, SUI, BNB, and XRP"""
    btc_price, btc_24h, btc_1h = btc_data
    sui_price, sui_24h, sui_1h = sui_data
    bnb_price, bnb_24h, bnb_1h = bnb_data
    xrp_price, xrp_24h, xrp_1h = xrp_data

    lines = []

    # Format BTC
    if btc_price is not None:
        btc_str = f"BTC ${btc_price:,.0f} [{btc_24h:+.2f}%] [{btc_1h:+.2f}%]"
        lines.append(btc_str)
    else:
        lines.append("BTC: Data N/A")

    # Format SUI
    if sui_price is not None:
        sui_str = f"SUI ${sui_price:.3f} [{sui_24h:+.2f}%] [{sui_1h:+.2f}%]"
        lines.append(sui_str)
    else:
        lines.append("SUI: Data N/A")

    # Format BNB
    if bnb_price is not None:
        bnb_str = f"BNB ${bnb_price:,.2f} [{bnb_24h:+.2f}%] [{bnb_1h:+.2f}%]"
        lines.append(bnb_str)
    else:
        lines.append("BNB: Data N/A")

    # Format XRP
    if xrp_price is not None:
        xrp_str = f"XRP ${xrp_price:.3f} [{xrp_24h:+.2f}%] [{xrp_1h:+.2f}%]"
        lines.append(xrp_str)
    else:
        lines.append("XRP: Data N/A")

    # Join with newline for compact display
    message = "\n".join(lines)

    return message


def send_telegram_notification(bot_token, chat_id, message):
    """Send message via Telegram Bot API"""
    try:
        # Telegram Bot API endpoint
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        # Prepare payload
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

        # Send POST request
        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 200:
            print(f"Notification sent successfully!")
            print(f"Message: {message}")
            result = response.json()
            if result.get('ok'):
                print(f"Telegram response: Message delivered (ID: {result['result']['message_id']})")
            return True
        else:
            print(f"Failed to send notification. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"Network error while sending notification: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


def main():
    """Main execution function"""
    print("=" * 50)
    print("Crypto Price Notification System")
    print("=" * 50)

    # Read environment variables
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    # Validate environment variables
    if not bot_token or not chat_id:
        print("ERROR: Missing required environment variables!")
        print("   Required: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        sys.exit(1)

    print(f"Bot Token: {bot_token[:10]}****")
    print(f"Chat ID: {chat_id}")
    print()

    # Fetch crypto data
    btc_data, sui_data, bnb_data, xrp_data = fetch_stock_data()

    # Display fetched data
    btc_price, btc_24h, btc_1h = btc_data
    sui_price, sui_24h, sui_1h = sui_data
    bnb_price, bnb_24h, bnb_1h = bnb_data
    xrp_price, xrp_24h, xrp_1h = xrp_data

    print()
    if btc_price is not None:
        print(f"BTC: ${btc_price:,.2f}, 24h: {btc_24h:+.2f}%, 1h: {btc_1h:+.2f}%")
    else:
        print("BTC: Could not fetch data")

    if sui_price is not None:
        print(f"SUI: ${sui_price:.3f}, 24h: {sui_24h:+.2f}%, 1h: {sui_1h:+.2f}%")
    else:
        print("SUI: Could not fetch data")

    if bnb_price is not None:
        print(f"BNB: ${bnb_price:,.2f}, 24h: {bnb_24h:+.2f}%, 1h: {bnb_1h:+.2f}%")
    else:
        print("BNB: Could not fetch data")

    if xrp_price is not None:
        print(f"XRP: ${xrp_price:.3f}, 24h: {xrp_24h:+.2f}%, 1h: {xrp_1h:+.2f}%")
    else:
        print("XRP: Could not fetch data")

    # Format message
    message = format_message(btc_data, sui_data, bnb_data, xrp_data)
    print()
    print("Message Preview:")
    print("-" * 30)
    print(message)
    print("-" * 30)
    print()

    # Send notification
    print("Sending Telegram notification...")
    success = send_telegram_notification(bot_token, chat_id, message)

    if success:
        print("Process completed successfully!")
        sys.exit(0)
    else:
        print("Process completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
