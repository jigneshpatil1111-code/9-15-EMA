import os
import sys
import time
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def test_dhan_websocket():
    from dhanhq import DhanContext, MarketFeed
    
    client_id = os.getenv("DHAN_CLIENT_ID")
    access_token = os.getenv("DHAN_ACCESS_TOKEN")
    
    context = DhanContext(client_id, access_token)
    instrument_list = [(MarketFeed.NSE, "2885"), (MarketFeed.NSE, "11536")]
    
    def on_connect(ws, message):
        print(f"[WebSocket] Connected! message: {message}")
        
    def on_message(ws, message):
        print(f"[WebSocket] Tick Data: {message}")
        
    def on_error(ws, error):
        print(f"[WebSocket] Error: {error}")
        
    def on_close(ws, message=None):
        print(f"[WebSocket] Closed: {message}")

    try:
        feed = MarketFeed(
            context,
            instrument_list,
            on_connect=on_connect,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        print("Connecting to WebSocket with await...")
        
        task = asyncio.create_task(feed.connect())
        
        await asyncio.sleep(5)
        await feed.disconnect()
        print("Test Complete.")
    except Exception as e:
        print(f"WebSocket test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_dhan_websocket())
