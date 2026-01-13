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
        btc = yf.Ticker("BTC-USD")

        # Get 24h data for current price and 24h change
        btc_24h = btc.history(period="2d")
        if btc_24h.empty or len(btc_24h) < 2:
            return None, None, None

        current_price = btc_24h['Close'].iloc[-1]
        price_24h_ago = btc_24h['Close'].iloc[-2]
        change_24h = ((current_price - price_24h_ago) / price_24h_ago) * 100

        # Get 15-minute data for 15min change
        btc_15m = btc.history(period="1d", interval="15m")
        if btc_15m.empty or len(btc_15m) < 2:
            change_15m = 0.0
        else:
            price_15m_ago = btc_15m['Close'].iloc[-2]
            change_15m = ((current_price - price_15m_ago) / price_15m_ago) * 100

        return current_price, change_24h, change_15m

    except Exception as e:
        print(f"Error fetching stock data: {e}")
        return None, None, None


def format_message(price, change_24h, change_15m):
    """Format message for small wearable screen with percentage changes"""
    if price is None:
        timestamp = datetime.now().strftime("%H:%M")
        return f"📉 Data Unavailable\n{timestamp}"

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
            print(f"✅ Notification sent successfully!")
            print(f"Message: {message}")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"❌ Failed to send notification. Status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error while sending notification: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
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
        print("❌ ERROR: Missing required environment variables!")
        print("   Required: INSTANCE_ID, API_TOKEN, and PHONE_NUMBER")
        sys.exit(1)

    print(f"📱 Instance: {instance_id}")
    print(f"🔑 API Token: {api_token[:4]}****")
    print(f"📞 Phone: {phone_number}")
    print()

    # Fetch stock data
    print("📊 Fetching BTC price and percentage changes...")
    price, change_24h, change_15m = fetch_stock_data()

    if price is None:
        print("⚠️  Warning: Could not fetch BTC data, sending error notification")
    else:
        print(f"💰 Price: ${price:,.2f}")
        print(f"📈 24h Change: {change_24h:+.2f}%")
        print(f"⚡ 15m Change: {change_15m:+.2f}%")

    # Format message
    message = format_message(price, change_24h, change_15m)
    print()
    print("📝 Message Preview:")
    print("-" * 30)
    print(message)
    print("-" * 30)
    print()

    # Send notification
    print("📤 Sending WhatsApp notification...")
    success = send_whatsapp_notification(instance_id, api_token, phone_number, message)

    if success:
        print("✅ Process completed successfully!")
        sys.exit(0)
    else:
        print("❌ Process completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
