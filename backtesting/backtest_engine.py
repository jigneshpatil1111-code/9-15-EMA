"""
Backtesting Engine.
Replays historical data day by day, applying both strategies,
quality filters, and scoring — then computes performance metrics.
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional, Callable

import pandas as pd
import numpy as np

from core.broker_base import Instrument
from strategies.one_percent_setup import OnePercentSetup
from strategies.ema_pullback_setup import EMAPullbackSetup
from strategies.base_strategy import Signal
from engine.quality_filter import QualityFilter
from engine.signal_scorer import SignalScorer
from backtesting.backtest_data import BacktestDataLoader
from config.settings import settings

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Full backtesting engine that replays historical data.

    Periods supported:
    - 6 Months
    - 1 Year
    - 2 Years

    Metrics computed:
    - Win Rate
    - Profit Factor
    - Max Drawdown
    - Average RR
    - Total Return
    - Monthly Return
    - Yearly Return
    """

    def __init__(self, data_loader: BacktestDataLoader):
        self._data_loader = data_loader
        self._strategies = [OnePercentSetup(), EMAPullbackSetup()]
        self._quality_filter = QualityFilter()
        self._signal_scorer = SignalScorer()

    def run_backtest(
        self,
        instruments: List[Instrument],
        period_months: int = 6,
        initial_capital: float = 100000.0,
        max_signals_per_day: int = 5,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        Run a full backtest over the specified period.

        Args:
            instruments: List of instruments to test.
            period_months: Backtest period in months (6, 12, or 24).
            initial_capital: Starting capital.
            max_signals_per_day: Max signals per day.
            progress_callback: Optional callback(current_day, total_days).

        Returns:
            Dict with comprehensive backtest results.
        """
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=period_months * 30)

        logger.info(
            f"Starting backtest: {start_date} to {end_date} "
            f"({period_months} months, {len(instruments)} instruments)"
        )

        # Load historical data
        logger.info("Loading historical data...")
        all_data = self._data_loader.load_bulk_data(
            instruments, start_date, end_date, use_cache=True
        )

        if not all_data:
            return {"status": "error", "message": "No historical data available."}

        # Get all unique trading days from any instrument
        all_days = set()
        for sym, df in all_data.items():
            days = self._data_loader.get_trading_days(df)
            all_days.update(days)
        trading_days = sorted(all_days)

        if not trading_days:
            return {"status": "error", "message": "No trading days found in data."}

        logger.info(f"Backtesting over {len(trading_days)} trading days...")

        # Run the backtest day by day
        all_trades: List[Dict] = []
        daily_pnl: List[Dict] = []
        capital = initial_capital

        for day_idx, current_day in enumerate(trading_days):
            day_signals = []

            for sym, data in all_data.items():
                try:
                    day_candles = self._data_loader.get_daily_candles(data, current_day)
                    if day_candles.empty or len(day_candles) < 3:
                        continue

                    prev_close = self._data_loader.get_previous_close(data, current_day)
                    if prev_close <= 0:
                        continue

                    # Find matching instrument
                    inst = next(
                        (i for i in instruments if i.symbol == sym), None
                    )
                    if not inst:
                        continue

                    # Run strategies
                    for strategy in self._strategies:
                        try:
                            signal = strategy.scan(
                                symbol=sym,
                                security_id=inst.security_id,
                                candles=day_candles,
                                prev_close=prev_close,
                            )
                            if signal:
                                # Quality filter
                                passed, _ = self._quality_filter.filter(
                                    signal, day_candles
                                )
                                if passed:
                                    self._signal_scorer.score(signal)
                                    day_signals.append((signal, day_candles))
                        except Exception:
                            continue

                except Exception:
                    continue

            # Rank and select top signals
            if day_signals:
                day_signals.sort(key=lambda x: x[0].signal_score, reverse=True)
                top = day_signals[:max_signals_per_day]

                for signal, candles in top:
                    trade_result = self._simulate_trade(signal, candles)
                    all_trades.append(trade_result)
                    capital += trade_result["pnl"]

            day_pnl = sum(
                t["pnl"]
                for t in all_trades
                if t.get("date") == current_day
            )
            daily_pnl.append({
                "date": current_day,
                "pnl": round(day_pnl, 2),
                "cumulative": round(capital - initial_capital, 2),
                "capital": round(capital, 2),
            })

            if progress_callback:
                progress_callback(day_idx + 1, len(trading_days))

        # Calculate metrics
        metrics = self._calculate_metrics(
            all_trades, daily_pnl, initial_capital, start_date, end_date
        )

        logger.info(
            f"Backtest complete: {metrics['total_trades']} trades, "
            f"Win Rate: {metrics['win_rate']:.1f}%, "
            f"P&L: ₹{metrics['total_pnl']:.2f}"
        )

        return {
            "status": "success",
            "period": f"{start_date} to {end_date}",
            "period_months": period_months,
            "initial_capital": initial_capital,
            "final_capital": round(capital, 2),
            "metrics": metrics,
            "trades": all_trades,
            "daily_pnl": daily_pnl,
        }

    def _simulate_trade(
        self, signal: Signal, candles: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Simulate a single trade execution on historical data.

        Walks forward from the entry candle checking:
        1. Stop loss hit
        2. Target hit
        3. Breakeven timeout (for 1% setup)
        4. EOD close at 15:15-15:25
        """
        entry_idx = signal.candle_index
        entry_price = signal.entry_price
        stop_loss = signal.stop_loss
        target = signal.target1
        pnl = 0.0
        exit_price = entry_price
        exit_reason = "eod_close"
        candles_held = 0

        for i in range(entry_idx + 1, len(candles)):
            candle = candles.iloc[i]
            candles_held += 1

            # Check stop loss
            if candle["low"] <= stop_loss:
                exit_price = stop_loss
                exit_reason = "stop_loss"
                break

            # Check target
            if candle["high"] >= target:
                exit_price = target
                exit_reason = "target_hit"
                break

            # Breakeven check for 1% setup
            if signal.setup_type == "1_pct_setup":
                if candles_held >= settings.ONE_PCT_BREAKEVEN_CANDLES:
                    move_pct = abs(
                        (candle["close"] - entry_price) / entry_price
                    ) * 100
                    if move_pct < 0.3:
                        exit_price = entry_price
                        exit_reason = "breakeven_timeout"
                        break

            # EOD close (last few candles of the day)
            if i >= len(candles) - 2:
                exit_price = candle["close"]
                exit_reason = "eod_close"
                break

        pnl = exit_price - entry_price

        return {
            "symbol": signal.symbol,
            "date": signal.timestamp.date() if hasattr(signal.timestamp, "date") else date.today(),
            "setup_type": signal.setup_type,
            "entry_price": round(entry_price, 2),
            "stop_loss": round(stop_loss, 2),
            "target": round(target, 2),
            "exit_price": round(exit_price, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round((pnl / entry_price) * 100, 2) if entry_price > 0 else 0.0,
            "risk_reward": signal.risk_reward,
            "rr_achieved": round(pnl / (entry_price - stop_loss), 2) if (entry_price - stop_loss) > 0 else 0.0,
            "exit_reason": exit_reason,
            "candles_held": candles_held,
            "signal_score": signal.signal_score,
            "result": "win" if pnl > 0 else ("loss" if pnl < 0 else "breakeven"),
        }

    def _calculate_metrics(
        self,
        trades: List[Dict],
        daily_pnl: List[Dict],
        initial_capital: float,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """Calculate comprehensive backtest metrics."""
        if not trades:
            return {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "breakeven": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "profit_factor": 0.0,
                "max_drawdown": 0.0,
                "max_drawdown_pct": 0.0,
                "avg_rr": 0.0,
                "total_return_pct": 0.0,
            }

        wins = [t for t in trades if t["pnl"] > 0]
        losses = [t for t in trades if t["pnl"] < 0]
        breakevens = [t for t in trades if t["pnl"] == 0]
        total = len(trades)

        gross_profit = sum(t["pnl"] for t in wins)
        gross_loss = abs(sum(t["pnl"] for t in losses))
        total_pnl = sum(t["pnl"] for t in trades)

        # Max drawdown
        cumulative = []
        running = 0.0
        for t in trades:
            running += t["pnl"]
            cumulative.append(running)

        peak = 0.0
        max_dd = 0.0
        for c in cumulative:
            peak = max(peak, c)
            dd = peak - c
            max_dd = max(max_dd, dd)

        # Monthly returns
        trade_df = pd.DataFrame(trades)
        monthly_returns = {}
        if not trade_df.empty and "date" in trade_df.columns:
            trade_df["month"] = pd.to_datetime(trade_df["date"]).dt.to_period("M")
            monthly = trade_df.groupby("month")["pnl"].sum()
            monthly_returns = {
                str(m): round(v, 2) for m, v in monthly.items()
            }

        # By setup
        setup_metrics = {}
        for setup in ["1_pct_setup", "ema_pullback"]:
            setup_trades = [t for t in trades if t["setup_type"] == setup]
            st_total = len(setup_trades)
            st_wins = len([t for t in setup_trades if t["pnl"] > 0])
            setup_metrics[setup] = {
                "total": st_total,
                "wins": st_wins,
                "win_rate": round(st_wins / st_total * 100, 1) if st_total > 0 else 0.0,
                "pnl": round(sum(t["pnl"] for t in setup_trades), 2),
            }

        return {
            "total_trades": total,
            "wins": len(wins),
            "losses": len(losses),
            "breakeven": len(breakevens),
            "win_rate": round(len(wins) / total * 100, 1) if total > 0 else 0.0,
            "total_pnl": round(total_pnl, 2),
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else 0.0,
            "max_drawdown": round(max_dd, 2),
            "max_drawdown_pct": round(max_dd / initial_capital * 100, 2) if initial_capital > 0 else 0.0,
            "avg_rr": round(sum(t["rr_achieved"] for t in trades) / total, 2) if total > 0 else 0.0,
            "total_return_pct": round(total_pnl / initial_capital * 100, 2) if initial_capital > 0 else 0.0,
            "avg_pnl_per_trade": round(total_pnl / total, 2) if total > 0 else 0.0,
            "largest_winner": round(max(t["pnl"] for t in trades), 2) if trades else 0.0,
            "largest_loser": round(min(t["pnl"] for t in trades), 2) if trades else 0.0,
            "avg_candles_held": round(sum(t["candles_held"] for t in trades) / total, 1) if total > 0 else 0.0,
            "monthly_returns": monthly_returns,
            "by_setup": setup_metrics,
        }
