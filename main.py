#!/usr/bin/env python3
"""
Stock Market Notification System for Huawei Band 10
Fetches BTC-USD price and sends to WhatsApp via CallMeBot API
"""

import os
import sys
from urllib.parse import quote
import requests
import yfinance as yf
from datetime import datetime


def fetch_stock_data():
    """Fetch current price for BTC-USD"""
    try:
        # Fetch Bitcoin price
        btc = yf.Ticker("BTC-USD")
        btc_data = btc.history(period="1d")

        if btc_data.empty:
            btc_price = "N/A"
        else:
            btc_price = f"${btc_data['Close'].iloc[-1]:,.2f}"

        return btc_price

    except Exception as e:
        print(f"Error fetching stock data: {e}")
        return None


def format_message(btc_price):
    """Format message for small wearable screen with emojis"""
    timestamp = datetime.now().strftime("%H:%M")

    # Compact format optimized for small screens
    if btc_price:
        message = f"🚀 BTC {timestamp}\n\n"
        message += f"₿ {btc_price}"
    else:
        message = f"📉 Data Unavailable\n{timestamp}"

    return message


def send_whatsapp_notification(phone_number, api_key, message):
    """Send message via CallMeBot WhatsApp API"""
    try:
        # URL encode the message
        encoded_message = quote(message)

        # CallMeBot API endpoint
        url = f"https://api.callmebot.com/whatsapp.php?phone={phone_number}&text={encoded_message}&apikey={api_key}"

        # Send GET request
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            print(f"✅ Notification sent successfully!")
            print(f"Message: {message}")
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
    phone_number = os.environ.get("PHONE_NUMBER")
    api_key = os.environ.get("API_KEY")

    # Validate environment variables
    if not phone_number or not api_key:
        print("❌ ERROR: Missing required environment variables!")
        print("   Required: PHONE_NUMBER and API_KEY")
        sys.exit(1)

    print(f"📱 Phone: {phone_number[:4]}****{phone_number[-2:]}")
    print(f"🔑 API Key: {api_key[:4]}****")
    print()

    # Fetch stock data
    print("📊 Fetching BTC price...")
    btc_price = fetch_stock_data()

    if btc_price is None:
        print("⚠️  Warning: Could not fetch BTC data, sending error notification")

    # Format message
    message = format_message(btc_price)
    print()
    print("📝 Message Preview:")
    print("-" * 30)
    print(message)
    print("-" * 30)
    print()

    # Send notification
    print("📤 Sending WhatsApp notification...")
    success = send_whatsapp_notification(phone_number, api_key, message)

    if success:
        print("✅ Process completed successfully!")
        sys.exit(0)
    else:
        print("❌ Process completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    main()
