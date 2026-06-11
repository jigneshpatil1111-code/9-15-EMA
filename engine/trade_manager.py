"""
Trade Manager.
Tracks open signals, monitors target/stop-loss hits,
enforces breakeven exit logic, and handles forced intraday close.

Now integrated with:
- OrderExecutor: Places actual (or paper) orders via Dhan API
- RiskManager: Enforces position sizing and loss limits
"""

import logging
import threading
from datetime import datetime, time as dt_time
from typing import List, Optional, Dict

import pytz

from strategies.base_strategy import Signal
from config.settings import settings

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")


class TradeManager:
    """
    Manages the lifecycle of trade signals from entry to exit.

    Responsibilities:
    - Track open trades in memory.
    - Monitor each trade for target hits, stop-loss hits.
    - Apply breakeven exit logic (1% Setup: no move in 4-5 candles).
    - Force-close all trades between 15:15 and 15:25 IST.
    - Record trade outcomes.
    """

    def __init__(self):
        self._open_trades: Dict[str, Signal] = {}  # keyed by symbol
        self._closed_trades: List[Signal] = []
        self._lock = threading.Lock()
        self._trade_db = None  # Set externally to trade_repository
        self._order_executor = None  # Set externally
        self._risk_manager = None  # Set externally

    def set_trade_repository(self, repo):
        """Set the database repository for persisting trades."""
        self._trade_db = repo

    def set_order_executor(self, executor):
        """Set the order executor for placing trades."""
        self._order_executor = executor

    def set_risk_manager(self, risk_mgr):
        """Set the risk manager for trade validation."""
        self._risk_manager = risk_mgr

    def add_trade(self, signal: Signal) -> bool:
        """
        Add a new trade signal to active monitoring and place the order.

        Flow:
        1. Check risk limits (via RiskManager)
        2. Calculate quantity (via RiskManager)
        3. Place order (via OrderExecutor)
        4. Track the trade

        Args:
            signal: The trade signal to track.

        Returns:
            True if trade was successfully added and order placed.
        """
        with self._lock:
            if signal.symbol in self._open_trades:
                logger.warning(
                    f"Trade already open for {signal.symbol}. Skipping duplicate."
                )
                return False

            # ── Risk Check ──
            if self._risk_manager:
                allowed, reason = self._risk_manager.can_take_trade(signal)
                if not allowed:
                    logger.info(
                        f"🚫 Trade BLOCKED by Risk Manager for {signal.symbol}: {reason}"
                    )
                    return False

                # Calculate quantity based on capital allocation
                signal.quantity = self._risk_manager.calculate_quantity(signal)
                if signal.quantity <= 0:
                    logger.warning(f"Quantity calculated as 0 for {signal.symbol}. Skipping.")
                    return False
            else:
                # Fallback: default quantity of 1 if no risk manager
                signal.quantity = 1

            # ── Place Order ──
            order_placed = False
            if self._order_executor:
                try:
                    if getattr(settings, 'USE_SUPER_ORDERS', True):
                        # Super Order: Entry + SL + Target in one call
                        result = self._order_executor.place_super_order(
                            security_id=signal.security_id,
                            symbol=signal.symbol,
                            quantity=signal.quantity,
                            entry_price=signal.entry_price,
                            stop_loss_price=signal.stop_loss,
                            target_price=signal.target1,
                        )
                    else:
                        # Regular limit order
                        result = self._order_executor.place_intraday_buy(
                            security_id=signal.security_id,
                            symbol=signal.symbol,
                            quantity=signal.quantity,
                            price=signal.entry_price,
                            order_type="LIMIT",
                        )

                    if result.success:
                        signal.order_id = result.order_id
                        signal.sl_order_id = result.sl_order_id
                        signal.target_order_id = result.target_order_id
                        signal.is_paper_trade = result.is_paper
                        order_placed = True
                        logger.info(
                            f"{'📝' if result.is_paper else '✅'} Order placed for "
                            f"{signal.symbol}: {signal.quantity} shares @ ₹{signal.entry_price:.2f}"
                        )
                    else:
                        logger.error(
                            f"❌ Order FAILED for {signal.symbol}: {result.message}"
                        )
                        return False

                except Exception as e:
                    logger.error(f"❌ Order placement error for {signal.symbol}: {e}")
                    return False
            else:
                # No order executor — signal-only mode (backward compatible)
                order_placed = True
                logger.info(f"Signal-only mode: {signal.symbol} (no order executor)")

            signal.status = "active"
            signal.entry_candle_count = 0
            self._open_trades[signal.symbol] = signal

            # Register with risk manager
            if self._risk_manager:
                self._risk_manager.register_trade_opened()

            logger.info(
                f"Trade added: {signal.symbol} | Qty: {signal.quantity} | "
                f"Entry: ₹{signal.entry_price} | SL: ₹{signal.stop_loss} | "
                f"T1: ₹{signal.target1} | {'PAPER' if signal.is_paper_trade else 'LIVE'}"
            )

            # Persist to database
            if self._trade_db:
                try:
                    self._trade_db.insert_trade(signal)
                except Exception as e:
                    logger.error(f"Failed to persist trade {signal.symbol}: {e}")

            return True

    def update_trades(self, ltp_map: Dict[str, float], candles_elapsed: int = 1):
        """
        Update all open trades with current market prices.
        Checks for target hits, stop-loss hits, and breakeven conditions.

        Args:
            ltp_map: Dict mapping symbol to current LTP.
            candles_elapsed: Number of new candles since last check.
        """
        with self._lock:
            symbols_to_close = []

            for symbol, trade in self._open_trades.items():
                ltp = ltp_map.get(symbol, 0.0)
                if ltp <= 0:
                    continue

                trade.entry_candle_count += candles_elapsed

                # ── Check Stop Loss ──
                if ltp <= trade.stop_loss:
                    trade.exit_price = trade.stop_loss
                    trade.exit_reason = "stop_loss"
                    trade.pnl = (trade.exit_price - trade.entry_price) * max(trade.quantity, 1)
                    symbols_to_close.append(symbol)
                    logger.info(
                        f"STOP LOSS hit: {symbol} @ {trade.stop_loss} | "
                        f"PnL: ₹{trade.pnl:.2f}"
                    )
                    continue

                # ── Check Target 1 ──
                if ltp >= trade.target1:
                    trade.exit_price = trade.target1
                    trade.exit_reason = "target1_hit"
                    trade.pnl = (trade.exit_price - trade.entry_price) * max(trade.quantity, 1)
                    symbols_to_close.append(symbol)
                    logger.info(
                        f"TARGET 1 hit: {symbol} @ {trade.target1} | "
                        f"PnL: ₹{trade.pnl:.2f}"
                    )
                    continue

                # ── Check Target 2 (if target 1 was a partial) ──
                if ltp >= trade.target2:
                    trade.exit_price = trade.target2
                    trade.exit_reason = "target2_hit"
                    trade.pnl = (trade.exit_price - trade.entry_price) * max(trade.quantity, 1)
                    symbols_to_close.append(symbol)
                    logger.info(
                        f"TARGET 2 hit: {symbol} @ {trade.target2} | "
                        f"PnL: ₹{trade.pnl:.2f}"
                    )
                    continue

                # ── Breakeven Exit (1% Setup only) ──
                if (
                    trade.setup_type == "1_pct_setup"
                    and trade.entry_candle_count >= settings.ONE_PCT_BREAKEVEN_CANDLES
                ):
                    # Check if price hasn't moved significantly from entry
                    move_pct = abs((ltp - trade.entry_price) / trade.entry_price) * 100
                    if move_pct < 0.3:  # Less than 0.3% movement = no meaningful move
                        trade.exit_price = trade.entry_price  # Breakeven
                        trade.exit_reason = "breakeven_timeout"
                        trade.pnl = 0.0
                        symbols_to_close.append(symbol)
                        logger.info(
                            f"BREAKEVEN exit: {symbol} — no movement in "
                            f"{trade.entry_candle_count} candles"
                        )
                        continue

            # Close trades
            for symbol in symbols_to_close:
                self._close_trade(symbol)

    def force_close_all(self, ltp_map: Dict[str, float]):
        """
        Force close all open trades (end of day).
        Called between 15:15 and 15:25 IST.

        Args:
            ltp_map: Dict mapping symbol to current LTP for exit pricing.
        """
        with self._lock:
            symbols_to_close = list(self._open_trades.keys())

            for symbol in symbols_to_close:
                trade = self._open_trades[symbol]
                ltp = ltp_map.get(symbol, trade.entry_price)
                trade.exit_price = ltp if ltp > 0 else trade.entry_price
                trade.exit_reason = "forced_eod_close"
                trade.pnl = (trade.exit_price - trade.entry_price) * trade.quantity

                # Place sell order for forced close
                if self._order_executor and trade.quantity > 0:
                    try:
                        self._order_executor.place_intraday_sell(
                            security_id=trade.security_id,
                            symbol=trade.symbol,
                            quantity=trade.quantity,
                            price=trade.exit_price,
                            order_type="MARKET",
                        )
                    except Exception as e:
                        logger.error(f"Force close sell order error for {symbol}: {e}")

                self._close_trade(symbol)

                logger.info(
                    f"FORCED CLOSE: {symbol} | Qty: {trade.quantity} | "
                    f"Exit: ₹{trade.exit_price} | PnL: ₹{trade.pnl:.2f}"
                )

    def _close_trade(self, symbol: str):
        """
        Move a trade from open to closed.
        Must be called within the lock.
        """
        if symbol in self._open_trades:
            trade = self._open_trades.pop(symbol)
            trade.status = "closed"
            trade.exit_time = datetime.now(IST)
            self._closed_trades.append(trade)

            # Register with risk manager
            if self._risk_manager:
                self._risk_manager.register_trade_closed(trade.pnl)

            # Persist to database
            if self._trade_db:
                try:
                    self._trade_db.update_trade_exit(trade)
                except Exception as e:
                    logger.error(f"Failed to update trade exit {symbol}: {e}")

    def should_force_close(self) -> bool:
        """
        Check if it's time to force-close all trades (15:15 - 15:25 IST).
        """
        now = datetime.now(IST)
        h_start, m_start = settings.get_force_exit_start_parts()
        h_end, m_end = settings.get_force_exit_end_parts()

        force_start = dt_time(h_start, m_start)
        force_end = dt_time(h_end, m_end)
        current = now.time()

        return force_start <= current <= force_end

    def is_signal_time_allowed(self) -> bool:
        """
        Check if new signals are allowed (before 14:30 IST).
        """
        now = datetime.now(IST)
        h_cutoff, m_cutoff = settings.get_signal_cutoff_parts()
        cutoff = dt_time(h_cutoff, m_cutoff)
        h_open, m_open = settings.get_market_open_parts()
        market_open = dt_time(h_open, m_open)

        current = now.time()
        return market_open <= current <= cutoff

    def get_open_trades(self) -> List[Signal]:
        """Get list of currently open trades."""
        with self._lock:
            return list(self._open_trades.values())

    def get_closed_trades(self) -> List[Signal]:
        """Get list of all closed trades."""
        with self._lock:
            return list(self._closed_trades)

    def get_today_pnl(self) -> float:
        """Calculate total P&L for today's closed trades."""
        with self._lock:
            return sum(t.pnl for t in self._closed_trades)

    def get_today_stats(self) -> Dict:
        """Get today's trading statistics."""
        with self._lock:
            closed = self._closed_trades
            if not closed:
                return {
                    "total_trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "breakeven": 0,
                    "win_rate": 0.0,
                    "total_pnl": 0.0,
                    "avg_rr": 0.0,
                    "best_trade": 0.0,
                    "worst_trade": 0.0,
                    "open_count": len(self._open_trades),
                }

            wins = [t for t in closed if t.pnl > 0]
            losses = [t for t in closed if t.pnl < 0]
            breakeven = [t for t in closed if t.pnl == 0]
            total = len(closed)

            return {
                "total_trades": total,
                "wins": len(wins),
                "losses": len(losses),
                "breakeven": len(breakeven),
                "win_rate": round(len(wins) / total * 100, 1) if total > 0 else 0.0,
                "total_pnl": round(sum(t.pnl for t in closed), 2),
                "avg_rr": round(
                    sum(t.risk_reward for t in closed) / total, 2
                )
                if total > 0
                else 0.0,
                "best_trade": round(max(t.pnl for t in closed), 2) if closed else 0.0,
                "worst_trade": round(min(t.pnl for t in closed), 2) if closed else 0.0,
                "open_count": len(self._open_trades),
            }

    def has_open_trade(self, symbol: str) -> bool:
        """Check if there's already an open trade for a given symbol."""
        with self._lock:
            return symbol in self._open_trades

    def get_open_pnl(self, ltp_map: Dict[str, float]) -> float:
        """Calculate unrealized P&L for all open trades."""
        with self._lock:
            total = 0.0
            for symbol, trade in self._open_trades.items():
                ltp = ltp_map.get(symbol, trade.entry_price)
                total += ltp - trade.entry_price
            return round(total, 2)
