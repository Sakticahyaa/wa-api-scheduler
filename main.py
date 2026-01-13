#!/usr/bin/env python3
"""
Stock Market Notification System for Huawei Band 10
Fetches BTC-USD price and sends to WhatsApp via Ultramsg API
"""

import os
import sys
import requests
import yfinance as yf
from datetime import datetime


def fetch_stock_data():
    """Fetch current price and percentage changes for BTC-USD"""
    try:
        # Use CoinGecko API (free, no API key needed, more reliable for crypto)
        print("  Fetching from CoinGecko API...")

        # Get current price and 24h change
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_24hr_change=true"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            print(f"  Error: CoinGecko API returned status {response.status_code}")
            return None, None, None

        data = response.json()

        if 'bitcoin' not in data:
            print(f"  Error: Bitcoin data not found in response")
            return None, None, None

        current_price = data['bitcoin']['usd']
        change_24h = data['bitcoin']['usd_24h_change']

        # For 15-minute change, use yfinance as fallback (or set to 0 if fails)
        try:
            print("  Fetching 15min data from yfinance...")
            btc = yf.Ticker("BTC-USD")
            btc_15m = btc.history(period="1d", interval="15m")

            if not btc_15m.empty and len(btc_15m) >= 2:
                latest_price = btc_15m['Close'].iloc[-1]
                price_15m_ago = btc_15m['Close'].iloc[-2]
                change_15m = ((latest_price - price_15m_ago) / price_15m_ago) * 100
            else:
                print(f"  Warning: Not enough 15min data. Using 0%")
                change_15m = 0.0
        except:
            print(f"  Warning: Could not fetch 15min data. Using 0%")
            change_15m = 0.0

        print(f"  Success! Price: ${current_price:,.2f}, 24h: {change_24h:+.2f}%, 15m: {change_15m:+.2f}%")
        return current_price, change_24h, change_15m

    except Exception as e:
        print(f"  Error fetching stock data: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


def format_message(price, change_24h, change_15m):
    """Format message for small wearable screen with percentage changes"""
    if price is None:
        timestamp = datetime.now().strftime("%H:%M")
        return f"Data Unavailable\n{timestamp}"

    # Format price with comma separator
    price_str = f"${price:,.0f}"

    # Format 24h change with +/- sign
    change_24h_str = f"{change_24h:+.1f}%"

    # Format 15min change with +/- sign
    change_15m_str = f"{change_15m:+.1f}%"

    # Compact format: BTC $92,142 [+2.5%] [-0.3%]
    message = f"BTC {price_str} [{change_24h_str}] [{change_15m_str}]"

    return message


def send_whatsapp_notification(instance_id, api_token, phone_number, message):
    """Send message via Ultramsg WhatsApp API"""
    try:
        # Ultramsg API endpoint
        url = f"https://api.ultramsg.com/{instance_id}/messages/chat"

        # Prepare payload
        payload = {
            "token": api_token,
            "to": phone_number,
            "body": message
        }

        # Send POST request
        response = requests.post(url, data=payload, timeout=10)

        if response.status_code == 200:
            print(f"Notification sent successfully!")
            print(f"Message: {message}")
            print(f"Response: {response.json()}")
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
    print("Stock Market Notification System")
    print("=" * 50)

    # Read environment variables
    instance_id = os.environ.get("INSTANCE_ID")
    api_token = os.environ.get("API_TOKEN")
    phone_number = os.environ.get("PHONE_NUMBER")

    # Validate environment variables
    if not instance_id or not api_token or not phone_number:
        print("ERROR: Missing required environment variables!")
        print("   Required: INSTANCE_ID, API_TOKEN, and PHONE_NUMBER")
        sys.exit(1)

    print(f"Instance: {instance_id}")
    print(f"API Token: {api_token[:4]}****")
    print(f"Phone: {phone_number}")
    print()

    # Fetch stock data
    print("Fetching BTC price and percentage changes...")
    price, change_24h, change_15m = fetch_stock_data()

    if price is None:
        print("Warning: Could not fetch BTC data, sending error notification")
    else:
        print(f"Price: ${price:,.2f}")
        print(f"24h Change: {change_24h:+.2f}%")
        print(f"15m Change: {change_15m:+.2f}%")

    # Format message
    message = format_message(price, change_24h, change_15m)
    print()
    print("Message Preview:")
    print("-" * 30)
    print(message)
    print("-" * 30)
    print()

    # Send notification
    print("Sending WhatsApp notification...")
    success = send_whatsapp_notification(instance_id, api_token, phone_number, message)

    if success:
        print("Process completed successfully!")
        sys.exit(0)
    else:
        print("Process completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
