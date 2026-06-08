# Dhan API Integration Guide

## Step 1: Create a Dhan Account

1. Visit [dhan.co](https://dhan.co) and create a trading account
2. Complete KYC verification
3. Fund your account (not required for data-only use)

## Step 2: Generate API Credentials

1. Log in to [web.dhan.co](https://web.dhan.co)
2. Go to **Profile** → **API Access**
3. Enable API access
4. Generate an **Access Token**
5. Note your **Client ID** (displayed on the API page)

## Step 3: Subscribe to Data API

1. On the Dhan dashboard, go to **API** → **Data API**
2. Subscribe to the **Market Data API** plan
3. This enables:
   - REST API for historical/intraday data
   - WebSocket for live market feed
   - Up to 5,000 instrument subscriptions per WebSocket connection

## Step 4: Configure .env

```env
DHAN_CLIENT_ID=your_client_id_here
DHAN_ACCESS_TOKEN=your_access_token_here
```

## API Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| Market Quote | LTP, OHLC, previous close |
| Intraday Minute Data | Today's 5-minute candles |
| Historical Minute Data | Past candle data for backtesting |
| WebSocket Feed | Real-time LTP for 500 instruments |

## Security Master

The system automatically downloads the Dhan security master CSV to map
Nifty 500 trading symbols to Dhan `security_id` values:
```
https://images.dhan.co/api-data/api-scrip-master.csv
```

This is refreshed daily on startup.

## Rate Limits

- REST API: ~10 requests/second
- WebSocket: 5 connections, 5000 instruments per connection
- The scanner includes built-in rate limiting (0.35s between calls)

## Token Refresh

Dhan access tokens expire periodically. When your token expires:
1. Go to [web.dhan.co](https://web.dhan.co) → Profile → API Access
2. Generate a new access token
3. Update `DHAN_ACCESS_TOKEN` in your `.env` file
4. Restart the scanner

## Troubleshooting

- **Authentication error:** Regenerate access token from Dhan dashboard
- **No data returned:** Ensure Data API subscription is active
- **WebSocket disconnects:** The scanner auto-reconnects up to 10 times
- **Security ID not found:** The security master CSV may be stale; delete the cached file in `data/` to force re-download
