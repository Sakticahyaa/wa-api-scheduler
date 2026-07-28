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
    """Fetch BTC and XAUT in a single batch call to avoid rate limiting"""
    import time
    print("Fetching all crypto prices in batch...")

    try:
        # Single batch call for both cryptos (price + 24h change)
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,tether-gold&vs_currencies=usd&include_24hr_change=true"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            print(f"  Batch API returned status {response.status_code}: {response.text[:100]}")
            return None

        data = response.json()
        print(f"  Successfully fetched both cryptos in one call")

        # Extract data for each crypto
        results = {}
        for symbol, coin_id in [("BTC", "bitcoin"), ("XAUT", "tether-gold")]:
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


def fetch_ihsg_data():
    """Fetch IHSG (Jakarta Composite Index) price and change via Yahoo Finance"""
    try:
        print("  [IHSG] Fetching from Yahoo Finance...")
        ticker = yf.Ticker("^JKSE")
        hist = ticker.history(period="5d", interval="1h")

        if hist.empty:
            print("  [IHSG] No data returned")
            return None, None, None

        current_price = float(hist['Close'].iloc[-1])

        # Change since previous close (market isn't open 24h, unlike crypto)
        prev_close = ticker.fast_info.get("previousClose") if hasattr(ticker.fast_info, "get") else None
        if not prev_close:
            prev_close = getattr(ticker.fast_info, "previous_close", None)
        change_24h = ((current_price - prev_close) / prev_close) * 100 if prev_close else 0.0

        # 1h change from the most recent two hourly candles (during market hours)
        change_1h = 0.0
        if len(hist) >= 2:
            price_1h_ago = float(hist['Close'].iloc[-2])
            change_1h = ((current_price - price_1h_ago) / price_1h_ago) * 100

        print(f"  [IHSG] Success! Price: {current_price:,.2f}, since prev close: {change_24h:+.2f}%, 1h: {change_1h:+.2f}%")
        return current_price, change_24h, change_1h

    except Exception as e:
        print(f"  [IHSG] Failed: {e}")
        return None, None, None


def fetch_stock_data():
    """Fetch BTC, XAUT, and IHSG prices"""
    import time
    print("Fetching prices...")

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

        xaut_price = batch_data["XAUT"]["price"] if batch_data["XAUT"] else None
        xaut_24h = batch_data["XAUT"]["change_24h"] if batch_data["XAUT"] else 0
        xaut_1h = 0.0
        if xaut_price:
            time.sleep(2)
            xaut_1h = fetch_1h_change("XAUT", "tether-gold")

        ihsg_price, ihsg_24h, ihsg_1h = fetch_ihsg_data()

        return (btc_price, btc_24h, btc_1h), (xaut_price, xaut_24h, xaut_1h), (ihsg_price, ihsg_24h, ihsg_1h)

    # Fallback to individual fetches if batch fails
    print("  Batch fetch failed, trying individual fetches...")

    # Fetch BTC
    print("\n  Fetching BTC...")
    btc_price, btc_24h, btc_1h = fetch_crypto_price("BTC", "BTCUSDT", "bitcoin")
    time.sleep(3)

    # Fetch XAUT
    print("\n  Fetching XAUT...")
    xaut_price, xaut_24h, xaut_1h = fetch_crypto_price("XAUT", "XAUTUSDT", "tether-gold")

    # Fetch IHSG
    ihsg_price, ihsg_24h, ihsg_1h = fetch_ihsg_data()

    return (btc_price, btc_24h, btc_1h), (xaut_price, xaut_24h, xaut_1h), (ihsg_price, ihsg_24h, ihsg_1h)


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


def format_message(btc_data, xaut_data, ihsg_data):
    """Format message for small wearable screen with BTC, XAUT, and IHSG"""
    btc_price, btc_24h, btc_1h = btc_data
    xaut_price, xaut_24h, xaut_1h = xaut_data
    ihsg_price, ihsg_24h, ihsg_1h = ihsg_data

    lines = []

    # Format BTC
    if btc_price is not None:
        btc_str = f"BTC ${btc_price:,.0f} [{btc_24h:+.2f}%] [{btc_1h:+.2f}%]"
        lines.append(btc_str)
    else:
        lines.append("BTC: Data N/A")

    # Format XAUT
    if xaut_price is not None:
        xaut_str = f"XAUT ${xaut_price:,.2f} [{xaut_24h:+.2f}%] [{xaut_1h:+.2f}%]"
        lines.append(xaut_str)
    else:
        lines.append("XAUT: Data N/A")

    # Format IHSG
    if ihsg_price is not None:
        ihsg_str = f"IHSG {ihsg_price:,.2f} [{ihsg_24h:+.2f}%] [{ihsg_1h:+.2f}%]"
        lines.append(ihsg_str)
    else:
        lines.append("IHSG: Data N/A")

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

    # Fetch price data
    btc_data, xaut_data, ihsg_data = fetch_stock_data()

    # Display fetched data
    btc_price, btc_24h, btc_1h = btc_data
    xaut_price, xaut_24h, xaut_1h = xaut_data
    ihsg_price, ihsg_24h, ihsg_1h = ihsg_data

    print()
    if btc_price is not None:
        print(f"BTC: ${btc_price:,.2f}, 24h: {btc_24h:+.2f}%, 1h: {btc_1h:+.2f}%")
    else:
        print("BTC: Could not fetch data")

    if xaut_price is not None:
        print(f"XAUT: ${xaut_price:,.2f}, 24h: {xaut_24h:+.2f}%, 1h: {xaut_1h:+.2f}%")
    else:
        print("XAUT: Could not fetch data")

    if ihsg_price is not None:
        print(f"IHSG: {ihsg_price:,.2f}, since prev close: {ihsg_24h:+.2f}%, 1h: {ihsg_1h:+.2f}%")
    else:
        print("IHSG: Could not fetch data")

    # Format message
    message = format_message(btc_data, xaut_data, ihsg_data)
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
