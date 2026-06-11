import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

def test_dhan_websocket():
    from dhanhq import DhanContext, MarketFeed
    
    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_ACCESS_TOKEN")
    
    if not client_id or not access_token:
        print("Missing Dhan API credentials in .env")
        return
        
    print(f"Testing with Client ID: {client_id}")
    context = DhanContext(client_id, access_token)
    
    # Nifty 50 and Bank Nifty generic tokens (just as a quick test)
    # E.g. Reliance: 2885, TCS: 11536
    sub_dict = {MarketFeed.NSE: ["2885", "11536"]}
    
    def on_connect(message):
        print(f"[WebSocket] Connected! message: {message}")
        
    def on_message(message):
        print(f"[WebSocket] Tick Data: {message}")
        
    def on_error(error):
        print(f"[WebSocket] Error: {error}")
        
    def on_close(message):
        print(f"[WebSocket] Closed: {message}")

    try:
        print("Initializing MarketFeed...")
        feed = MarketFeed(
            context,
            sub_dict,
            on_connect=on_connect,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        print("Connecting to WebSocket...")
        feed.connect()
        
        # It runs synchronously or asynchronously depending on dhanhq version
        # We just sleep to keep the script alive for a few seconds if it's threaded
        time.sleep(10)
        feed.disconnect()
        print("Test Complete.")
    except Exception as e:
        print(f"WebSocket test failed: {e}")

if __name__ == "__main__":
    test_dhan_websocket()
