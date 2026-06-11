"""
Central configuration module.
Loads all settings from environment variables / .env file using Pydantic.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── Broker: Dhan API ──────────────────────────────────────────
    DHAN_CLIENT_ID: str = Field(default="", description="Dhan API Client ID")
    DHAN_ACCESS_TOKEN: str = Field(default="", description="Dhan API Access Token")

    # ── Broker Selection ──────────────────────────────────────────
    BROKER: str = Field(default="dhan", description="Active broker: dhan, kite, upstox")

    # ── Kite Connect (fallback) ───────────────────────────────────
    KITE_API_KEY: str = Field(default="", description="Kite Connect API Key")
    KITE_API_SECRET: str = Field(default="", description="Kite Connect API Secret")
    KITE_ACCESS_TOKEN: str = Field(default="", description="Kite Connect Access Token")

    # ── Upstox (fallback) ─────────────────────────────────────────
    UPSTOX_API_KEY: str = Field(default="", description="Upstox API Key")
    UPSTOX_API_SECRET: str = Field(default="", description="Upstox API Secret")
    UPSTOX_ACCESS_TOKEN: str = Field(default="", description="Upstox Access Token")

    # ── Telegram ──────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = Field(default="", description="Telegram Bot Token")
    TELEGRAM_CHAT_ID: str = Field(default="", description="Telegram Chat ID")

    # ── Database ──────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql://scanner:scanner_password@localhost:5432/intraday_scanner",
        description="PostgreSQL connection string",
    )

    # ── Trading Hours (IST, HH:MM) ───────────────────────────────
    MARKET_OPEN: str = Field(default="09:15", description="Market open time IST")
    SIGNAL_CUTOFF: str = Field(default="14:30", description="No new signals after this time IST")
    FORCE_EXIT_START: str = Field(default="15:15", description="Force exit start time IST")
    FORCE_EXIT_END: str = Field(default="15:25", description="Force exit end time IST")
    REPORT_TIME: str = Field(default="15:30", description="Daily report generation time IST")

    # ── Market Sentiment ──────────────────────────────────────────
    SENTIMENT_BULLISH_THRESHOLD: int = Field(
        default=300,
        description="Minimum positive stocks for bullish market",
    )

    # ── Signal Limits ─────────────────────────────────────────────
    MAX_SIGNALS_PER_SCAN: int = Field(default=5, description="Maximum signals per scan cycle")

    # ── Strategy 1: 1% Setup ─────────────────────────────────────
    ONE_PCT_MAX_RANGE: float = Field(default=1.0, description="Max first candle range %")
    ONE_PCT_RR_TARGET1: float = Field(default=3.0, description="Target 1 risk-reward")
    ONE_PCT_RR_TARGET2: float = Field(default=4.0, description="Target 2 risk-reward")
    ONE_PCT_BREAKEVEN_CANDLES: int = Field(
        default=5, description="Exit at breakeven if no move in N candles"
    )

    # ── Strategy 2: 9/15 EMA Pullback ────────────────────────────
    EMA_FAST_PERIOD: int = Field(default=9, description="Fast EMA period")
    EMA_SLOW_PERIOD: int = Field(default=15, description="Slow EMA period")
    EMA_PULLBACK_RR_MIN: float = Field(default=2.5, description="Min RR for EMA pullback")
    EMA_PULLBACK_RR_MAX: float = Field(default=3.0, description="Max RR for EMA pullback")
    EMA_PULLBACK_RR_TARGET: float = Field(default=2.75, description="Default RR target")

    # ── Quality Filters ───────────────────────────────────────────
    OVERSIZED_CANDLE_MULTIPLIER: float = Field(
        default=2.0, description="Candle body > N * avg range = oversized"
    )
    VOLUME_AVG_PERIOD: int = Field(default=20, description="Volume averaging lookback period")
    MIN_LIQUIDITY_LAKHS: float = Field(
        default=50.0, description="Min liquidity: price * volume in lakhs"
    )
    MAX_SPREAD_PCT: float = Field(default=0.5, description="Max bid-ask spread %")
    MAX_EMA_DISTANCE_PCT: float = Field(
        default=1.5, description="Max distance from EMA 9 in %"
    )
    MAX_CONSECUTIVE_GREEN: int = Field(
        default=5, description="Momentum exhaustion: max consecutive green candles"
    )
    ABNORMAL_CANDLE_MULTIPLIER: float = Field(
        default=3.0, description="Candle > N * avg range = abnormal"
    )
    MIN_RR_ONE_PCT: float = Field(default=3.0, description="Min RR for 1% setup")
    MIN_RR_EMA_PULLBACK: float = Field(default=2.0, description="Min RR for EMA pullback")

    # ── Scanner ───────────────────────────────────────────────────
    SCAN_INTERVAL_SECONDS: int = Field(default=300, description="Scan interval in seconds")

    # ── Order Execution ──────────────────────────────────────────
    PAPER_TRADING: bool = Field(
        default=True,
        description="Paper trading mode: True = simulated orders, False = live orders",
    )
    USE_SUPER_ORDERS: bool = Field(
        default=True,
        description="Use Super Orders (Entry + SL + Target in one call)",
    )

    # ── Risk Management ──────────────────────────────────────────
    MAX_DAILY_LOSS: float = Field(
        default=5000.0, description="Max daily loss in INR before kill switch activates"
    )
    MAX_POSITION_SIZE: float = Field(
        default=50000.0, description="Max position value in INR per trade"
    )
    MAX_OPEN_POSITIONS: int = Field(
        default=3, description="Max concurrent open positions"
    )
    CAPITAL_PER_TRADE: float = Field(
        default=25000.0, description="Capital allocated per trade in INR"
    )
    MAX_TRADES_PER_DAY: int = Field(
        default=10, description="Max number of trades per day"
    )

    # ── Logging ───────────────────────────────────────────────────
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FILE: str = Field(default="logs/scanner.log", description="Log file path")

    # ── Paths ─────────────────────────────────────────────────────
    BASE_DIR: str = Field(
        default=str(Path(__file__).resolve().parent.parent),
        description="Project root directory",
    )
    DATA_DIR: str = Field(default="data", description="Data directory for cached files")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

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
