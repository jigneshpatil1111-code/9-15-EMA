-- ============================================================
-- INTRADAY SCANNER - PostgreSQL Schema
-- ============================================================
-- This is a fallback for manual database setup.
-- SQLAlchemy ORM will auto-create tables via init_database().
-- ============================================================

CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    security_id VARCHAR(50) NOT NULL,
    trade_date DATE NOT NULL,
    entry_time TIMESTAMP NOT NULL,
    exit_time TIMESTAMP,
    setup_type VARCHAR(50) NOT NULL,
    entry_price DOUBLE PRECISION NOT NULL,
    stop_loss DOUBLE PRECISION NOT NULL,
    target1 DOUBLE PRECISION NOT NULL,
    target2 DOUBLE PRECISION,
    exit_price DOUBLE PRECISION,
    quantity INTEGER DEFAULT 0,
    pnl DOUBLE PRECISION DEFAULT 0.0,
    pnl_pct DOUBLE PRECISION DEFAULT 0.0,
    risk_reward DOUBLE PRECISION DEFAULT 0.0,
    rr_achieved DOUBLE PRECISION DEFAULT 0.0,
    signal_score DOUBLE PRECISION DEFAULT 0.0,
    volume BIGINT DEFAULT 0,
    avg_volume DOUBLE PRECISION DEFAULT 0.0,
    ema9 DOUBLE PRECISION DEFAULT 0.0,
    ema15 DOUBLE PRECISION DEFAULT 0.0,
    distance_from_ema DOUBLE PRECISION DEFAULT 0.0,
    status VARCHAR(20) DEFAULT 'active',
    exit_reason VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS ix_trades_trade_date ON trades(trade_date);
CREATE INDEX IF NOT EXISTS ix_trades_setup_type ON trades(setup_type);
CREATE INDEX IF NOT EXISTS ix_trades_status ON trades(status);
CREATE INDEX IF NOT EXISTS ix_trades_date_status ON trades(trade_date, status);
CREATE INDEX IF NOT EXISTS ix_trades_symbol_date ON trades(symbol, trade_date);

CREATE TABLE IF NOT EXISTS trade_journal (
    id SERIAL PRIMARY KEY,
    trade_id INTEGER NOT NULL REFERENCES trades(id),
    journal_date DATE NOT NULL,
    screenshot_link TEXT,
    notes TEXT,
    trade_result VARCHAR(20),
    lessons_learned TEXT,
    market_conditions TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_trade_journal_trade_id ON trade_journal(trade_id);

CREATE TABLE IF NOT EXISTS daily_performance (
    id SERIAL PRIMARY KEY,
    performance_date DATE NOT NULL UNIQUE,
    total_trades INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    breakeven INTEGER DEFAULT 0,
    win_rate DOUBLE PRECISION DEFAULT 0.0,
    total_pnl DOUBLE PRECISION DEFAULT 0.0,
    gross_profit DOUBLE PRECISION DEFAULT 0.0,
    gross_loss DOUBLE PRECISION DEFAULT 0.0,
    profit_factor DOUBLE PRECISION DEFAULT 0.0,
    best_trade_pnl DOUBLE PRECISION DEFAULT 0.0,
    best_trade_symbol VARCHAR(50),
    worst_trade_pnl DOUBLE PRECISION DEFAULT 0.0,
    worst_trade_symbol VARCHAR(50),
    avg_rr DOUBLE PRECISION DEFAULT 0.0,
    max_drawdown DOUBLE PRECISION DEFAULT 0.0,
    sentiment_status VARCHAR(20),
    positive_stocks INTEGER DEFAULT 0,
    negative_stocks INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_daily_performance_date ON daily_performance(performance_date);

CREATE TABLE IF NOT EXISTS imported_reports (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    source VARCHAR(50) NOT NULL,
    import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    record_count INTEGER DEFAULT 0,
    total_pnl DOUBLE PRECISION DEFAULT 0.0,
    date_range_start DATE,
    date_range_end DATE,
    status VARCHAR(20) DEFAULT 'completed',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sentiment_logs (
    id SERIAL PRIMARY KEY,
    log_date DATE NOT NULL,
    log_time TIMESTAMP NOT NULL,
    positive_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    unchanged_count INTEGER DEFAULT 0,
    total_scanned INTEGER DEFAULT 0,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_sentiment_logs_date ON sentiment_logs(log_date);
