# Telegram Bot Setup Guide

## Step 1: Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a name for your bot (e.g., "My Trading Scanner")
4. Choose a username (e.g., `my_trading_scanner_bot`)
5. BotFather will give you a **Bot Token** — save this
   ```
   Example: 6123456789:ABCdefGhIjKlMnOpQrStUvWxYz
   ```

## Step 2: Get Your Chat ID

### Option A: Using @userinfobot
1. Search for **@userinfobot** on Telegram
2. Start a chat and send any message
3. It will reply with your **Chat ID**

### Option B: Using the API
1. Send any message to your bot
2. Open this URL in your browser (replace YOUR_BOT_TOKEN):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
3. Find `"chat": {"id": 123456789}` in the response
4. That number is your Chat ID

### Option C: Group Chat
1. Add your bot to a Telegram group
2. Send a message in the group
3. Use the `getUpdates` API above
4. The group Chat ID will be a negative number (e.g., `-1001234567890`)

## Step 3: Configure .env

```env
TELEGRAM_BOT_TOKEN=6123456789:ABCdefGhIjKlMnOpQrStUvWxYz
TELEGRAM_CHAT_ID=123456789
```

## Step 4: Test Connection

Run the scanner — it will send a test message on startup:
```
🤖 Intraday Scanner Bot
━━━━━━━━━━━━━━━━━━━━
✅ Connection test successful!
Bot is online and ready to send alerts.
━━━━━━━━━━━━━━━━━━━━
```

## Alert Format

Trade alerts look like this:
```
🚀 LONG TRADE ALERT
━━━━━━━━━━━━━━━━━━━━
📊 Stock: RELIANCE
📋 Setup: 1% Setup
💰 Entry: ₹2,850.50
🛑 Stop Loss: ₹2,835.00
🎯 Target 1: ₹2,897.00
🎯 Target 2: ₹2,912.50
📐 Risk Reward: 1:3.0
📊 Volume: 5.25 L
⭐ Signal Score: 82/100
🕐 Time: 09:35:00
━━━━━━━━━━━━━━━━━━━━
```

## Troubleshooting

- **Bot not responding:** Ensure you've started a chat with the bot first (send `/start`)
- **Wrong Chat ID:** Use the `getUpdates` API method to verify
- **Token expired:** Generate a new token via BotFather (`/token` command)
- **Rate limited:** Telegram allows ~30 messages/second per bot
