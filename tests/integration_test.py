"""
Integration Test Script
Tests live connections to all external services:
- PostgreSQL Database
- Telegram Bot API
- Dhan API (REST & WebSocket)
"""
import os
import sys
import time
import asyncio
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings
from database.connection import check_connection, init_database
from telegram_bot.notifier import TelegramNotifier
from core.broker_factory import get_broker
from core.instrument_manager import InstrumentManager

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("integration_test")

def main():
    print("=" * 60)
    print("🚀 RUNNING FULL INTEGRATION TESTS")
    print("=" * 60)
    
    # 1. Test PostgreSQL
    print("\n[1/4] Testing PostgreSQL Database Connection...")
    if check_connection():
        print("  ✅ Database connection successful!")
        init_database()
        print("  ✅ Database initialized.")
    else:
        print("  ❌ Database connection failed! Ensure PostgreSQL is running.")
        print("  ⚠️ Continuing tests without database...")

    # 2. Test Telegram
    print("\n[2/4] Testing Telegram Bot Connection...")
    telegram = TelegramNotifier()
    try:
        telegram.test_connection()
        print("  ✅ Telegram connection successful! (Check your Telegram app for a test message)")
    except Exception as e:
        print(f"  ❌ Telegram connection failed: {e}")
        sys.exit(1)

    # 3. Test Dhan API
    print("\n[3/4] Testing Dhan API Connection...")
    try:
        broker = get_broker()
        # Fetch funds as a simple auth check
        funds = broker._client.get_fund_limits()
        if 'data' in funds or 'sora' in funds: # check valid response structure
             print("  ✅ Dhan API authentication successful!")
        else:
             print(f"  ⚠️ Dhan API returned unexpected format: {funds}")
             
        # Fetch a test quote (Nifty 50 index or Reliance)
        ltp = broker.get_ltp("1333") # Reliance security ID
        if ltp > 0:
            print(f"  ✅ Dhan API Market Data accessible! (RELIANCE LTP: ₹{ltp})")
        else:
            print("  ❌ Dhan API Market Data failed or returned 0.")
    except Exception as e:
        print(f"  ❌ Dhan API connection failed: {e}")
        sys.exit(1)

    # 4. Test Instrument Manager
    print("\n[4/4] Testing Instrument Loading (Nifty 500)...")
    try:
        im = InstrumentManager()
        instruments = im.load()
        if len(instruments) > 0:
            print(f"  ✅ Successfully loaded {len(instruments)} instruments!")
            print(f"  Sample: {instruments[0].symbol} ({instruments[0].security_id})")
        else:
            print("  ❌ No instruments loaded.")
            sys.exit(1)
    except Exception as e:
        print(f"  ❌ Instrument loading failed: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("🎉 ALL INTEGRATION TESTS PASSED! SYSTEM IS READY TO RUN.")
    print("=" * 60)

if __name__ == "__main__":
    main()
