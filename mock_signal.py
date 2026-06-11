import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from telegram_bot.notifier import TelegramNotifier
from strategies.base_strategy import Signal

def send_mock_signal():
    notifier = TelegramNotifier()
    
    # Create a mock signal for a 1% Strategy setup
    signal = Signal(
        symbol="TCS",
        security_id="11536",
        setup_type="1% Daily Momentum 🚀",
        entry_price=3900.00,
        stop_loss=3861.00,  # ~1% stop loss
        target1=3939.00,    # ~1% target
        target2=3978.00,    # ~2% target
        risk_reward=1.0,
        volume=250000,
        signal_score=9.8,
        ema9=3880.50,
        ema15=3870.20,
        avg_volume=200000,
        distance_from_ema=0.05,
        notes="Strong momentum breakout detected. Targeting quick 1% Intraday move.",
        timestamp=datetime.now()
    )
    
    print("Sending mock 1% Strategy signal to Telegram...")
    notifier.send_trade_alert(signal)
    print("Sent!")

if __name__ == "__main__":
    send_mock_signal()
