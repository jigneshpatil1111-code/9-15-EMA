"""
Trade repository.
CRUD operations and aggregation queries for all database models.
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import func, desc, asc, and_, extract
from sqlalchemy.orm import Session

from database.connection import get_session
from database.models import Trade, TradeJournal, DailyPerformance, SentimentLog, ImportedReport
from strategies.base_strategy import Signal

logger = logging.getLogger(__name__)


class TradeRepository:
    """Repository for all trade-related database operations."""

    def insert_trade(self, signal: Signal) -> int:
        """
        Insert a new trade from a signal.
        Returns the trade ID.
        """
        session = get_session()
        try:
            trade = Trade(
                symbol=signal.symbol,
                security_id=signal.security_id,
                trade_date=signal.timestamp.date() if hasattr(signal.timestamp, 'date') else date.today(),
                entry_time=signal.timestamp if isinstance(signal.timestamp, datetime) else datetime.now(),
                setup_type=signal.setup_type,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                target1=signal.target1,
                target2=signal.target2,
                risk_reward=signal.risk_reward,
                signal_score=signal.signal_score,
                volume=signal.volume,
                avg_volume=signal.avg_volume,
                ema9=signal.ema9,
                ema15=signal.ema15,
                distance_from_ema=signal.distance_from_ema,
                status="active",
                notes=signal.notes,
            )
            session.add(trade)
            session.commit()
            trade_id = trade.id
            logger.info(f"Inserted trade #{trade_id}: {signal.symbol}")
            return trade_id
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to insert trade {signal.symbol}: {e}")
            raise
        finally:
            session.close()

    def update_trade_exit(self, signal: Signal):
        """Update a trade with exit information."""
        session = get_session()
        try:
            trade = (
                session.query(Trade)
                .filter(
                    Trade.symbol == signal.symbol,
                    Trade.status == "active",
                )
                .order_by(desc(Trade.entry_time))
                .first()
            )
            if trade:
                trade.exit_price = signal.exit_price
                trade.exit_time = signal.exit_time or datetime.now()
                trade.pnl = signal.pnl
                trade.pnl_pct = (
                    (signal.pnl / signal.entry_price * 100)
                    if signal.entry_price > 0
                    else 0.0
                )
                risk = signal.entry_price - signal.stop_loss
                trade.rr_achieved = (
                    signal.pnl / risk if risk > 0 else 0.0
                )
                trade.status = "closed"
                trade.exit_reason = signal.exit_reason
                session.commit()
                logger.info(
                    f"Updated trade exit: {signal.symbol} | "
                    f"PnL: {signal.pnl:.2f} | Reason: {signal.exit_reason}"
                )
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update trade exit {signal.symbol}: {e}")
        finally:
            session.close()

    def get_trades_by_date(self, trade_date: date) -> List[Trade]:
        """Get all trades for a specific date."""
        session = get_session()
        try:
            trades = (
                session.query(Trade)
                .filter(Trade.trade_date == trade_date)
                .order_by(desc(Trade.entry_time))
                .all()
            )
            return trades
        finally:
            session.close()

    def get_trades_by_date_range(
        self, start_date: date, end_date: date
    ) -> List[Trade]:
        """Get all trades within a date range."""
        session = get_session()
        try:
            trades = (
                session.query(Trade)
                .filter(
                    Trade.trade_date >= start_date,
                    Trade.trade_date <= end_date,
                )
                .order_by(desc(Trade.entry_time))
                .all()
            )
            return trades
        finally:
            session.close()

    def get_closed_trades_by_date(self, trade_date: date) -> List[Trade]:
        """Get all closed trades for a specific date."""
        session = get_session()
        try:
            trades = (
                session.query(Trade)
                .filter(
                    Trade.trade_date == trade_date,
                    Trade.status == "closed",
                )
                .order_by(desc(Trade.exit_time))
                .all()
            )
            return trades
        finally:
            session.close()

    def get_active_trades(self) -> List[Trade]:
        """Get all currently active trades."""
        session = get_session()
        try:
            trades = (
                session.query(Trade)
                .filter(Trade.status == "active")
                .order_by(desc(Trade.entry_time))
                .all()
            )
            return trades
        finally:
            session.close()

    def get_daily_pnl(self, trade_date: date) -> float:
        """Calculate total P&L for a given date."""
        session = get_session()
        try:
            result = (
                session.query(func.sum(Trade.pnl))
                .filter(
                    Trade.trade_date == trade_date,
                    Trade.status == "closed",
                )
                .scalar()
            )
            return float(result or 0.0)
        finally:
            session.close()

    def get_weekly_pnl(self, reference_date: date = None) -> float:
        """Calculate total P&L for the current week."""
        if reference_date is None:
            reference_date = date.today()
        start_of_week = reference_date - timedelta(days=reference_date.weekday())
        session = get_session()
        try:
            result = (
                session.query(func.sum(Trade.pnl))
                .filter(
                    Trade.trade_date >= start_of_week,
                    Trade.trade_date <= reference_date,
                    Trade.status == "closed",
                )
                .scalar()
            )
            return float(result or 0.0)
        finally:
            session.close()

    def get_monthly_pnl(self, year: int, month: int) -> float:
        """Calculate total P&L for a given month."""
        session = get_session()
        try:
            result = (
                session.query(func.sum(Trade.pnl))
                .filter(
                    extract("year", Trade.trade_date) == year,
                    extract("month", Trade.trade_date) == month,
                    Trade.status == "closed",
                )
                .scalar()
            )
            return float(result or 0.0)
        finally:
            session.close()

    def get_yearly_pnl(self, year: int) -> float:
        """Calculate total P&L for a given year."""
        session = get_session()
        try:
            result = (
                session.query(func.sum(Trade.pnl))
                .filter(
                    extract("year", Trade.trade_date) == year,
                    Trade.status == "closed",
                )
                .scalar()
            )
            return float(result or 0.0)
        finally:
            session.close()

    def get_performance_stats(
        self, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """Calculate comprehensive performance statistics for a date range."""
        session = get_session()
        try:
            trades = (
                session.query(Trade)
                .filter(
                    Trade.trade_date >= start_date,
                    Trade.trade_date <= end_date,
                    Trade.status == "closed",
                )
                .all()
            )

            if not trades:
                return {
                    "total_trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "breakeven": 0,
                    "win_rate": 0.0,
                    "total_pnl": 0.0,
                    "gross_profit": 0.0,
                    "gross_loss": 0.0,
                    "profit_factor": 0.0,
                    "avg_rr": 0.0,
                    "max_drawdown": 0.0,
                    "best_trade": None,
                    "worst_trade": None,
                    "largest_winner": 0.0,
                    "largest_loser": 0.0,
                    "avg_holding_time": 0.0,
                }

            wins = [t for t in trades if t.pnl > 0]
            losses = [t for t in trades if t.pnl < 0]
            breakeven = [t for t in trades if t.pnl == 0]
            total = len(trades)

            gross_profit = sum(t.pnl for t in wins)
            gross_loss = abs(sum(t.pnl for t in losses))

            # Calculate max drawdown
            cumulative_pnl = []
            running = 0.0
            for t in sorted(trades, key=lambda x: x.entry_time):
                running += t.pnl
                cumulative_pnl.append(running)

            peak = 0.0
            max_dd = 0.0
            for pnl in cumulative_pnl:
                peak = max(peak, pnl)
                dd = peak - pnl
                max_dd = max(max_dd, dd)

            # Average holding time in minutes
            holding_times = []
            for t in trades:
                if t.entry_time and t.exit_time:
                    delta = t.exit_time - t.entry_time
                    holding_times.append(delta.total_seconds() / 60)
            avg_holding = sum(holding_times) / len(holding_times) if holding_times else 0.0

            # Best and worst trades
            best = max(trades, key=lambda t: t.pnl)
            worst = min(trades, key=lambda t: t.pnl)

            return {
                "total_trades": total,
                "wins": len(wins),
                "losses": len(losses),
                "breakeven": len(breakeven),
                "win_rate": round(len(wins) / total * 100, 1) if total > 0 else 0.0,
                "total_pnl": round(sum(t.pnl for t in trades), 2),
                "gross_profit": round(gross_profit, 2),
                "gross_loss": round(gross_loss, 2),
                "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0.0,
                "avg_rr": round(sum(t.rr_achieved for t in trades) / total, 2) if total > 0 else 0.0,
                "max_drawdown": round(max_dd, 2),
                "best_trade": {"symbol": best.symbol, "pnl": round(best.pnl, 2)},
                "worst_trade": {"symbol": worst.symbol, "pnl": round(worst.pnl, 2)},
                "largest_winner": round(best.pnl, 2),
                "largest_loser": round(worst.pnl, 2),
                "avg_holding_time": round(avg_holding, 1),
            }
        finally:
            session.close()

    def get_pnl_by_setup(self, start_date: date, end_date: date) -> Dict[str, Dict]:
        """Get P&L breakdown by setup type."""
        session = get_session()
        try:
            results = {}
            for setup in ["1_pct_setup", "ema_pullback"]:
                trades = (
                    session.query(Trade)
                    .filter(
                        Trade.trade_date >= start_date,
                        Trade.trade_date <= end_date,
                        Trade.setup_type == setup,
                        Trade.status == "closed",
                    )
                    .all()
                )
                total = len(trades)
                wins = len([t for t in trades if t.pnl > 0])
                results[setup] = {
                    "total": total,
                    "wins": wins,
                    "losses": total - wins,
                    "win_rate": round(wins / total * 100, 1) if total > 0 else 0.0,
                    "total_pnl": round(sum(t.pnl for t in trades), 2),
                }
            return results
        finally:
            session.close()

    def get_top_performers(
        self, start_date: date, end_date: date, limit: int = 10
    ) -> List[Dict]:
        """Get top performing stocks by total P&L."""
        session = get_session()
        try:
            results = (
                session.query(
                    Trade.symbol,
                    func.sum(Trade.pnl).label("total_pnl"),
                    func.count(Trade.id).label("trade_count"),
                )
                .filter(
                    Trade.trade_date >= start_date,
                    Trade.trade_date <= end_date,
                    Trade.status == "closed",
                )
                .group_by(Trade.symbol)
                .order_by(desc("total_pnl"))
                .limit(limit)
                .all()
            )
            return [
                {
                    "symbol": r.symbol,
                    "total_pnl": round(r.total_pnl, 2),
                    "trade_count": r.trade_count,
                }
                for r in results
            ]
        finally:
            session.close()

    def get_worst_performers(
        self, start_date: date, end_date: date, limit: int = 10
    ) -> List[Dict]:
        """Get worst performing stocks by total P&L."""
        session = get_session()
        try:
            results = (
                session.query(
                    Trade.symbol,
                    func.sum(Trade.pnl).label("total_pnl"),
                    func.count(Trade.id).label("trade_count"),
                )
                .filter(
                    Trade.trade_date >= start_date,
                    Trade.trade_date <= end_date,
                    Trade.status == "closed",
                )
                .group_by(Trade.symbol)
                .order_by(asc("total_pnl"))
                .limit(limit)
                .all()
            )
            return [
                {
                    "symbol": r.symbol,
                    "total_pnl": round(r.total_pnl, 2),
                    "trade_count": r.trade_count,
                }
                for r in results
            ]
        finally:
            session.close()

    def save_daily_performance(self, perf_date: date, stats: Dict):
        """Save or update daily performance record."""
        session = get_session()
        try:
            existing = (
                session.query(DailyPerformance)
                .filter(DailyPerformance.performance_date == perf_date)
                .first()
            )

            if existing:
                for key, value in stats.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
            else:
                perf = DailyPerformance(performance_date=perf_date, **stats)
                session.add(perf)

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save daily performance: {e}")
        finally:
            session.close()

    def save_sentiment_log(self, sentiment_data):
        """Save a sentiment evaluation log entry."""
        session = get_session()
        try:
            log = SentimentLog(
                log_date=sentiment_data.timestamp.date(),
                log_time=sentiment_data.timestamp,
                positive_count=sentiment_data.positive_count,
                negative_count=sentiment_data.negative_count,
                unchanged_count=sentiment_data.unchanged_count,
                total_scanned=sentiment_data.total_scanned,
                status=sentiment_data.status,
            )
            session.add(log)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save sentiment log: {e}")
        finally:
            session.close()

    def get_equity_curve(self, start_date: date, end_date: date) -> List[Dict]:
        """Get daily cumulative P&L for equity curve plotting."""
        session = get_session()
        try:
            results = (
                session.query(
                    Trade.trade_date,
                    func.sum(Trade.pnl).label("daily_pnl"),
                )
                .filter(
                    Trade.trade_date >= start_date,
                    Trade.trade_date <= end_date,
                    Trade.status == "closed",
                )
                .group_by(Trade.trade_date)
                .order_by(asc(Trade.trade_date))
                .all()
            )

            curve = []
            cumulative = 0.0
            for r in results:
                cumulative += float(r.daily_pnl)
                curve.append({
                    "date": r.trade_date,
                    "daily_pnl": round(float(r.daily_pnl), 2),
                    "cumulative_pnl": round(cumulative, 2),
                })
            return curve
        finally:
            session.close()

    def insert_imported_report(self, filename: str, source: str, record_count: int,
                                total_pnl: float, date_start: date, date_end: date) -> int:
        """Record an imported report."""
        session = get_session()
        try:
            report = ImportedReport(
                filename=filename,
                source=source,
                record_count=record_count,
                total_pnl=total_pnl,
                date_range_start=date_start,
                date_range_end=date_end,
            )
            session.add(report)
            session.commit()
            return report.id
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to insert imported report: {e}")
            raise
        finally:
            session.close()

    def insert_journal_entry(self, trade_id: int, notes: str = "",
                              screenshot_link: str = "", trade_result: str = ""):
        """Insert a trade journal entry."""
        session = get_session()
        try:
            journal = TradeJournal(
                trade_id=trade_id,
                journal_date=date.today(),
                notes=notes,
                screenshot_link=screenshot_link,
                trade_result=trade_result,
            )
            session.add(journal)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to insert journal entry: {e}")
        finally:
            session.close()

    def get_all_trades_dataframe(self, start_date: date, end_date: date):
        """Get all trades as a list of dicts for DataFrame conversion."""
        session = get_session()
        try:
            trades = (
                session.query(Trade)
                .filter(
                    Trade.trade_date >= start_date,
                    Trade.trade_date <= end_date,
                )
                .order_by(desc(Trade.entry_time))
                .all()
            )
            return [
                {
                    "id": t.id,
                    "symbol": t.symbol,
                    "date": t.trade_date,
                    "entry_time": t.entry_time,
                    "exit_time": t.exit_time,
                    "setup_type": t.setup_type,
                    "entry_price": t.entry_price,
                    "stop_loss": t.stop_loss,
                    "target1": t.target1,
                    "target2": t.target2,
                    "exit_price": t.exit_price,
                    "pnl": t.pnl,
                    "pnl_pct": t.pnl_pct,
                    "risk_reward": t.risk_reward,
                    "rr_achieved": t.rr_achieved,
                    "signal_score": t.signal_score,
                    "volume": t.volume,
                    "status": t.status,
                    "exit_reason": t.exit_reason,
                    "notes": t.notes,
                }
                for t in trades
            ]
        finally:
            session.close()
