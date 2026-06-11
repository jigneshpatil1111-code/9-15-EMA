import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add project root to sys path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

load_dotenv()

from core.broker_factory import get_broker
from telegram_bot.notifier import TelegramNotifier
from strategies.base_strategy import Signal

def send_real_price_mock():
    # Initialize Broker
    broker = get_broker()
    
    # Try fetching real previous close for RELIANCE (NSE: 2885)
    # 2885 is Reliance's security ID on NSE
    print("Fetching real price data from Dhan...")
    try:
        real_price = broker.get_previous_close("2885", "NSE_EQ")
        if real_price <= 0:
            real_price = 2850.0  # Fallback if API returns 0 out of hours
    except Exception as e:
        print(f"Error fetching real price: {e}")
        real_price = 2850.0
        
    print(f"Real Price Fetched for Reliance: {real_price}")
    
    notifier = TelegramNotifier()
    
    # Create a mock signal using REAL price
    entry_price = real_price
    
    # 9-15 EMA Setup usually has stop loss slightly below entry/swing low
    # Let's say 0.5% stop loss for Intraday
    stop_loss = round(entry_price * 0.995, 2) 
    
    # Target 1: 1:1 risk reward
    risk = entry_price - stop_loss
    target1 = round(entry_price + risk, 2)
    
    # Target 2: 1:2 risk reward
    target2 = round(entry_price + (risk * 2), 2)
    
    signal = Signal(
        symbol="RELIANCE",
        security_id="2885",
        setup_type="9-15 EMA Crossover 🟢",
        entry_price=entry_price,
        stop_loss=stop_loss,
        target1=target1,
        target2=target2,
        risk_reward=2.0,
        volume=125000,
        signal_score=9.5,
        ema9=round(entry_price * 0.999, 2),
        ema15=round(entry_price * 0.998, 2),
        avg_volume=100000,
        distance_from_ema=0.1,
        notes="Real Price test based on Last Closing Price. 9 EMA crossed above 15 EMA.",
        timestamp=datetime.now()
    )
    
    print("Sending real-price mock signal to Telegram...")
    notifier.send_trade_alert(signal)
    print("Sent!")

if __name__ == "__main__":
    send_real_price_mock()
