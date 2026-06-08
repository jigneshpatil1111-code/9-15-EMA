"""Check if credentials are configured (not placeholder values)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

checks = {
    "DHAN_CLIENT_ID": os.getenv("DHAN_CLIENT_ID", ""),
    "DHAN_ACCESS_TOKEN": os.getenv("DHAN_ACCESS_TOKEN", ""),
    "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN", ""),
    "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID", ""),
}

all_ok = True
for key, val in checks.items():
    is_placeholder = "your_" in val or val == ""
    status = "PLACEHOLDER" if is_placeholder else f"OK ({len(val)} chars)"
    print(f"  {key}: {status}")
    if is_placeholder:
        all_ok = False

if all_ok:
    print("\nAll credentials configured!")
else:
    print("\nSome credentials are still placeholders. Please update .env file.")
