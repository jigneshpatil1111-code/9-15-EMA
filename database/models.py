"""
SQLAlchemy ORM models for the trading system.
All trade data, journals, performance metrics, and imports are stored here.
"""

from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Date,
    Text,
    Boolean,
    BigInteger,
    Index,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Trade(Base):
    """Stores all trade signals and their outcomes."""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(50), nullable=False, index=True)
    security_id = Column(String(50), nullable=False)
    trade_date = Column(Date, nullable=False, index=True)
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=True)
    setup_type = Column(String(50), nullable=False, index=True)
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=False)
    target1 = Column(Float, nullable=False)
    target2 = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Integer, default=0)
    pnl = Column(Float, default=0.0)
    pnl_pct = Column(Float, default=0.0)
    risk_reward = Column(Float, default=0.0)
    rr_achieved = Column(Float, default=0.0)
    signal_score = Column(Float, default=0.0)
    volume = Column(BigInteger, default=0)
    avg_volume = Column(Float, default=0.0)
    ema9 = Column(Float, default=0.0)
    ema15 = Column(Float, default=0.0)
    distance_from_ema = Column(Float, default=0.0)
    status = Column(String(20), default="active", index=True)
    exit_reason = Column(String(50), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to journal
    journal_entry = relationship("TradeJournal", back_populates="trade", uselist=False)

    __table_args__ = (
        Index("ix_trades_date_status", "trade_date", "status"),
        Index("ix_trades_symbol_date", "symbol", "trade_date"),
    )

    def __repr__(self):
        return (
            f"<Trade(id={self.id}, symbol={self.symbol}, "
            f"entry={self.entry_price}, pnl={self.pnl}, status={self.status})>"
        )


class TradeJournal(Base):
    """Advanced trade journal entries linked to trades."""

    __tablename__ = "trade_journal"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(Integer, ForeignKey("trades.id"), nullable=False, index=True)
    journal_date = Column(Date, nullable=False)
    screenshot_link = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    trade_result = Column(String(20), nullable=True)  # win, loss, breakeven
    lessons_learned = Column(Text, nullable=True)
    market_conditions = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship back to trade
    trade = relationship("Trade", back_populates="journal_entry")

    def __repr__(self):
        return f"<TradeJournal(id={self.id}, trade_id={self.trade_id})>"


class DailyPerformance(Base):
    """Daily aggregated performance metrics."""

    __tablename__ = "daily_performance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    performance_date = Column(Date, nullable=False, unique=True, index=True)
    total_trades = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    breakeven = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    gross_profit = Column(Float, default=0.0)
    gross_loss = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    best_trade_pnl = Column(Float, default=0.0)
    best_trade_symbol = Column(String(50), nullable=True)
    worst_trade_pnl = Column(Float, default=0.0)
    worst_trade_symbol = Column(String(50), nullable=True)
    avg_rr = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    sentiment_status = Column(String(20), nullable=True)
    positive_stocks = Column(Integer, default=0)
    negative_stocks = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<DailyPerformance(date={self.performance_date}, "
            f"pnl={self.total_pnl}, win_rate={self.win_rate})>"
        )


class ImportedReport(Base):
    """Tracks imported Dhan P&L reports and tradebooks."""

    __tablename__ = "imported_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    source = Column(String(50), nullable=False)  # dhan_pnl, dhan_tradebook, contract_note
    import_date = Column(DateTime, default=datetime.utcnow)
    record_count = Column(Integer, default=0)
    total_pnl = Column(Float, default=0.0)
    date_range_start = Column(Date, nullable=True)
    date_range_end = Column(Date, nullable=True)
    status = Column(String(20), default="completed")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<ImportedReport(id={self.id}, filename={self.filename}, "
            f"records={self.record_count})>"
        )


class SentimentLog(Base):
    """Logs market sentiment evaluations."""

    __tablename__ = "sentiment_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    log_date = Column(Date, nullable=False, index=True)
    log_time = Column(DateTime, nullable=False)
    positive_count = Column(Integer, default=0)
    negative_count = Column(Integer, default=0)
    unchanged_count = Column(Integer, default=0)
    total_scanned = Column(Integer, default=0)
    status = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<SentimentLog(date={self.log_date}, "
            f"positive={self.positive_count}, status={self.status})>"
        )
