# Intraday Stock Scanner — Nifty 500

## Overview

Automated intraday stock scanning system for the Indian stock market.

- **Universe:** Nifty 500
- **Data Source:** Dhan API (live market data + WebSocket)
- **Strategies:** 1% Setup + 9/15 EMA Pullback Setup
- **Type:** LONG ONLY • INTRADAY ONLY
- **Alerts:** Telegram
- **Dashboard:** Streamlit
- **Database:** PostgreSQL

## Architecture

```
main.py                    → Entry point (runs scanner + scheduler)
├── core/                  → Broker abstraction, market feed, instruments
├── strategies/            → 1% Setup + EMA Pullback (exact rules)
├── engine/                → Sentiment engine, scanner, quality filter, scorer
├── indicators/            → EMA, volume, candle analysis
├── database/              → SQLAlchemy models, repository, migrations
├── telegram_bot/          → Alerts and reports
├── reports/               → Report generator, scheduler, exports
├── importer/              → Dhan P&L/tradebook import
├── backtesting/           → Historical backtest engine
├── dashboard/             → Streamlit app with 8 pages
│   └── pages/             → Sentiment, Signals, History, Performance, etc.
├── Dockerfile             → Scanner container
├── Dockerfile.dashboard   → Dashboard container
└── docker-compose.yml     → Full stack deployment
```

## Quick Start

### 1. Clone and Configure

```bash
cp .env.example .env
# Edit .env with your credentials:
# - DHAN_CLIENT_ID
# - DHAN_ACCESS_TOKEN
# - TELEGRAM_BOT_TOKEN
# - TELEGRAM_CHAT_ID
```

### 2. Run with Docker (Recommended)

```bash
docker-compose up -d
```

This starts:
- **PostgreSQL** on port 5432
- **Scanner** running main.py
- **Dashboard** on http://localhost:8501

### 3. Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL (ensure it's running)

# Run the scanner
python main.py

# In a separate terminal, run the dashboard
streamlit run dashboard/app.py
```

## Configuration

All settings are in `.env`. Key variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DHAN_CLIENT_ID` | Dhan API Client ID | (required) |
| `DHAN_ACCESS_TOKEN` | Dhan API Access Token | (required) |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token | (required) |
| `TELEGRAM_CHAT_ID` | Telegram Chat ID | (required) |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://scanner:scanner_password@localhost:5432/intraday_scanner` |
| `SENTIMENT_BULLISH_THRESHOLD` | Min positive stocks for bullish | 300 |
| `MAX_SIGNALS_PER_SCAN` | Max signals per scan cycle | 5 |
| `SCAN_INTERVAL_SECONDS` | Scan interval | 300 |

## Trading Rules

### Market Sentiment Gate
- Scans all Nifty 500 stocks
- Counts positive vs negative stocks
- **BULLISH (≥300 positive):** Scanning active
- **NEUTRAL (<300 positive):** No signals generated

### Strategy 1: 1% Setup
1. Gap-up open
2. First candle range < 1%
3. Second candle holds first candle low
4. Third/fourth candle closes above first candle body high
5. Entry candle not oversized, close to EMA 9
6. Volume above average
7. Entry → SL: Low of entry candle → Targets: 1:3 and 1:4 RR

### Strategy 2: 9/15 EMA Pullback
1. EMA 9 > EMA 15, both rising
2. Strong impulsive bullish move
3. Healthy pullback stays above EMA 15
4. Breakout above pullback high
5. Volume expansion, entry near EMA 9
6. Entry → SL: Low of entry candle → Target: 1:2.5 to 1:3 RR

### Intraday Enforcement
- Signals: 09:15 AM – 02:30 PM only
- Force close all trades: 03:15 PM – 03:25 PM
- No overnight holdings

## Dashboard Pages

1. **Market Sentiment** — Bullish/Neutral status, gauge chart
2. **Active Signals** — Live signals, open trades
3. **Trade History** — Filtered trade log with journal
4. **Performance** — Daily/Weekly/Monthly/Yearly P&L, equity curve
5. **Analytics** — Setup comparison, best/worst stocks, growth curves
6. **Backtesting** — Run historical backtests
7. **Import Data** — Upload Dhan reports (xlsx/csv)
8. **Reports** — Download reports in Excel/CSV/PDF

## Reports

Automatic reports sent to Telegram:
- **Daily:** at 15:30 IST
- **Weekly:** every Friday after close
- **Monthly:** last trading day of month
- **Yearly:** last trading day of year

## Setup Guides

- [Telegram Setup](setup_guides/telegram_setup.md)
- [Dhan API Guide](setup_guides/dhan_api_guide.md)
- [Deployment Guide](setup_guides/deployment_guide.md)

## License

Private — for personal trading use only.
