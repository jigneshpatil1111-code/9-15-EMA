"""
Central configuration module.
Loads all settings from environment variables / .env file using standard os.getenv.
"""

import os
from pathlib import Path

class Settings:
    """Application settings loaded from environment variables."""

    # ── Broker: Dhan API ──────────────────────────────────────────
    DHAN_CLIENT_ID: str = os.getenv("DHAN_CLIENT_ID", "")
    DHAN_ACCESS_TOKEN: str = os.getenv("DHAN_ACCESS_TOKEN", "")

    # ── Broker Selection ──────────────────────────────────────────
    BROKER: str = os.getenv("BROKER", "dhan")

    # ── Kite Connect (fallback) ───────────────────────────────────
    KITE_API_KEY: str = os.getenv("KITE_API_KEY", "")
    KITE_API_SECRET: str = os.getenv("KITE_API_SECRET", "")
    KITE_ACCESS_TOKEN: str = os.getenv("KITE_ACCESS_TOKEN", "")

    # ── Upstox (fallback) ─────────────────────────────────────────
    UPSTOX_API_KEY: str = os.getenv("UPSTOX_API_KEY", "")
    UPSTOX_API_SECRET: str = os.getenv("UPSTOX_API_SECRET", "")
    UPSTOX_ACCESS_TOKEN: str = os.getenv("UPSTOX_ACCESS_TOKEN", "")

    # ── Telegram ──────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

    # ── Database ──────────────────────────────────────────────────
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://scanner:scanner_password@localhost:5432/intraday_scanner")

    # ── Trading Hours (IST, HH:MM) ───────────────────────────────
    MARKET_OPEN: str = os.getenv("MARKET_OPEN", "09:15")
    SIGNAL_CUTOFF: str = os.getenv("SIGNAL_CUTOFF", "14:30")
    FORCE_EXIT_START: str = os.getenv("FORCE_EXIT_START", "15:15")
    FORCE_EXIT_END: str = os.getenv("FORCE_EXIT_END", "15:25")
    REPORT_TIME: str = os.getenv("REPORT_TIME", "15:30")

    # ── Market Sentiment ──────────────────────────────────────────
    SENTIMENT_BULLISH_THRESHOLD: int = int(os.getenv("SENTIMENT_BULLISH_THRESHOLD", "300"))

    # ── Signal Limits ─────────────────────────────────────────────
    MAX_SIGNALS_PER_SCAN: int = int(os.getenv("MAX_SIGNALS_PER_SCAN", "5"))

    # ── Strategy 1: 1% Setup ─────────────────────────────────────
    ONE_PCT_MAX_RANGE: float = float(os.getenv("ONE_PCT_MAX_RANGE", "1.0"))
    ONE_PCT_RR_TARGET1: float = float(os.getenv("ONE_PCT_RR_TARGET1", "3.0"))
    ONE_PCT_RR_TARGET2: float = float(os.getenv("ONE_PCT_RR_TARGET2", "4.0"))
    ONE_PCT_BREAKEVEN_CANDLES: int = int(os.getenv("ONE_PCT_BREAKEVEN_CANDLES", "5"))

    # ── Strategy 2: 9/15 EMA Pullback ────────────────────────────
    EMA_FAST_PERIOD: int = int(os.getenv("EMA_FAST_PERIOD", "9"))
    EMA_SLOW_PERIOD: int = int(os.getenv("EMA_SLOW_PERIOD", "15"))
    EMA_PULLBACK_RR_MIN: float = float(os.getenv("EMA_PULLBACK_RR_MIN", "2.5"))
    EMA_PULLBACK_RR_MAX: float = float(os.getenv("EMA_PULLBACK_RR_MAX", "3.0"))
    EMA_PULLBACK_RR_TARGET: float = float(os.getenv("EMA_PULLBACK_RR_TARGET", "2.75"))

    # ── Quality Filters ───────────────────────────────────────────
    OVERSIZED_CANDLE_MULTIPLIER: float = float(os.getenv("OVERSIZED_CANDLE_MULTIPLIER", "2.0"))
    VOLUME_AVG_PERIOD: int = int(os.getenv("VOLUME_AVG_PERIOD", "20"))
    MIN_LIQUIDITY_LAKHS: float = float(os.getenv("MIN_LIQUIDITY_LAKHS", "50.0"))
    MAX_SPREAD_PCT: float = float(os.getenv("MAX_SPREAD_PCT", "0.5"))
    MAX_EMA_DISTANCE_PCT: float = float(os.getenv("MAX_EMA_DISTANCE_PCT", "1.5"))
    MAX_CONSECUTIVE_GREEN: int = int(os.getenv("MAX_CONSECUTIVE_GREEN", "5"))
    ABNORMAL_CANDLE_MULTIPLIER: float = float(os.getenv("ABNORMAL_CANDLE_MULTIPLIER", "3.0"))
    MIN_RR_ONE_PCT: float = float(os.getenv("MIN_RR_ONE_PCT", "3.0"))
    MIN_RR_EMA_PULLBACK: float = float(os.getenv("MIN_RR_EMA_PULLBACK", "2.0"))

    # ── Scanner ───────────────────────────────────────────────────
    SCAN_INTERVAL_SECONDS: int = int(os.getenv("SCAN_INTERVAL_SECONDS", "300"))

    # ── Order Execution ──────────────────────────────────────────
    PAPER_TRADING: bool = os.getenv("PAPER_TRADING", "True").lower() in ("true", "1", "t")
    USE_SUPER_ORDERS: bool = os.getenv("USE_SUPER_ORDERS", "True").lower() in ("true", "1", "t")

    # ── Risk Management ──────────────────────────────────────────
    MAX_DAILY_LOSS: float = float(os.getenv("MAX_DAILY_LOSS", "5000.0"))
    MAX_POSITION_SIZE: float = float(os.getenv("MAX_POSITION_SIZE", "50000.0"))
    MAX_OPEN_POSITIONS: int = int(os.getenv("MAX_OPEN_POSITIONS", "3"))
    CAPITAL_PER_TRADE: float = float(os.getenv("CAPITAL_PER_TRADE", "25000.0"))
    MAX_TRADES_PER_DAY: int = int(os.getenv("MAX_TRADES_PER_DAY", "10"))

    # ── Logging ───────────────────────────────────────────────────
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/scanner.log")

    # ── Paths ─────────────────────────────────────────────────────
    BASE_DIR: str = str(Path(__file__).resolve().parent.parent)
    DATA_DIR: str = os.getenv("DATA_DIR", "data")

    # ── Derived helpers ───────────────────────────────────────────

    def get_market_open_parts(self) -> tuple:
        """Return (hour, minute) for market open."""
        parts = self.MARKET_OPEN.split(":")
        return int(parts[0]), int(parts[1])

    def get_signal_cutoff_parts(self) -> tuple:
        """Return (hour, minute) for signal cutoff."""
        parts = self.SIGNAL_CUTOFF.split(":")
        return int(parts[0]), int(parts[1])

    def get_force_exit_start_parts(self) -> tuple:
        """Return (hour, minute) for force exit start."""
        parts = self.FORCE_EXIT_START.split(":")
        return int(parts[0]), int(parts[1])

    def get_force_exit_end_parts(self) -> tuple:
        """Return (hour, minute) for force exit end."""
        parts = self.FORCE_EXIT_END.split(":")
        return int(parts[0]), int(parts[1])

    def get_report_time_parts(self) -> tuple:
        """Return (hour, minute) for report generation."""
        parts = self.REPORT_TIME.split(":")
        return int(parts[0]), int(parts[1])


# Singleton settings instance
settings = Settings()
