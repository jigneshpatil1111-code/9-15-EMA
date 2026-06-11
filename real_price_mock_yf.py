import os
import sys
from datetime import datetime
import yfinance as yf
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

load_dotenv()

from telegram_bot.notifier import TelegramNotifier
from strategies.base_strategy import Signal

def send_real_price_mock():
    # Fetch real price from Yahoo Finance
    print("Fetching REAL market price from yfinance...")
    ticker = yf.Ticker("RELIANCE.NS")
    hist = ticker.history(period="1d")
    
    if not hist.empty:
        real_price = round(hist['Close'].iloc[-1], 2)
    else:
        real_price = 2850.0  # Safe fallback just in case
        
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
        notes=f"REAL PRICE TEST. Actual CMP: {real_price}",
        timestamp=datetime.now()
    )
    
    print("Sending real-price mock signal to Telegram...")
    notifier.send_trade_alert(signal)
    print("Sent!")

if __name__ == "__main__":
    send_real_price_mock()
