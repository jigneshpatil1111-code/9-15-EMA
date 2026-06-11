"""
Risk Manager.
Enforces position sizing, daily loss limits, max open positions,
and capital allocation rules to protect the trading account.

Features:
- Max daily loss limit (kill switch)
- Max position size per trade
- Max concurrent open positions
- Capital per trade calculation (quantity sizing)
- Trade count limit per day
- Kill switch for emergency stop
"""

import logging
import threading
from datetime import datetime
from typing import Optional

import pytz

from strategies.base_strategy import Signal
from config.settings import settings

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")


class RiskManager:
    """
    Enforces risk management rules before any order is placed.

    All checks must pass before an order can proceed:
    1. Kill switch is not active
    2. Daily loss limit not breached
    3. Max open positions not exceeded
    4. Position size within limits
    5. Trade count within daily limit
    """

    def __init__(self):
        self._daily_realized_pnl: float = 0.0
        self._open_positions: int = 0
        self._trade_count_today: int = 0
        self._kill_switch: bool = False
        self._lock = threading.Lock()
        self._last_reset_date: Optional[datetime] = None

        # Load settings
        self._max_daily_loss = float(getattr(settings, "MAX_DAILY_LOSS", 5000))
        self._max_position_size = float(getattr(settings, "MAX_POSITION_SIZE", 50000))
        self._max_open_positions = int(getattr(settings, "MAX_OPEN_POSITIONS", 3))
        self._capital_per_trade = float(getattr(settings, "CAPITAL_PER_TRADE", 25000))
        self._max_trades_per_day = int(getattr(settings, "MAX_TRADES_PER_DAY", 10))

        logger.info(
            f"Risk Manager initialized: "
            f"Max Daily Loss=₹{self._max_daily_loss}, "
            f"Capital/Trade=₹{self._capital_per_trade}, "
            f"Max Positions={self._max_open_positions}, "
            f"Max Trades/Day={self._max_trades_per_day}"
        )

    def reset_daily(self):
        """Reset daily counters (called at start of each trading day)."""
        with self._lock:
            self._daily_realized_pnl = 0.0
            self._trade_count_today = 0
            self._kill_switch = False
            self._last_reset_date = datetime.now(IST)
            logger.info("Risk Manager: Daily state reset.")

    def can_take_trade(self, signal: Signal) -> tuple:
        """
        Check if a new trade is allowed based on risk rules.

        Args:
            signal: The trade signal to evaluate.

        Returns:
            (allowed: bool, reason: str) — True if trade is allowed.
        """
        with self._lock:
            # Check 1: Kill switch
            if self._kill_switch:
                return False, "Kill switch is ACTIVE. All trading suspended."

            # Check 2: Daily loss limit
            if self._daily_realized_pnl <= -self._max_daily_loss:
                self._kill_switch = True
                logger.warning(
                    f"🛑 DAILY LOSS LIMIT BREACHED! "
                    f"P&L: ₹{self._daily_realized_pnl:.2f} | "
                    f"Limit: -₹{self._max_daily_loss:.2f} | "
                    f"Kill switch activated."
                )
                return False, (
                    f"Daily loss limit breached: ₹{self._daily_realized_pnl:.2f} "
                    f"(limit: -₹{self._max_daily_loss:.2f})"
                )

            # Check 3: Max open positions
            if self._open_positions >= self._max_open_positions:
                return False, (
                    f"Max open positions reached: {self._open_positions}/"
                    f"{self._max_open_positions}"
                )

            # Check 4: Max trades per day
            if self._trade_count_today >= self._max_trades_per_day:
                return False, (
                    f"Max daily trades reached: {self._trade_count_today}/"
                    f"{self._max_trades_per_day}"
                )

            # Check 5: Position size limit
            trade_value = signal.entry_price * self.calculate_quantity(signal)
            if trade_value > self._max_position_size:
                return False, (
                    f"Position size ₹{trade_value:.0f} exceeds max "
                    f"₹{self._max_position_size:.0f}"
                )

            return True, "All risk checks passed."

    def calculate_quantity(self, signal: Signal) -> int:
        """
        Calculate the number of shares to buy based on capital per trade.

        Uses the configured CAPITAL_PER_TRADE to determine quantity.
        Ensures minimum quantity of 1.

        Args:
            signal: The trade signal.

        Returns:
            Number of shares to buy (integer, minimum 1).
        """
        if signal.entry_price <= 0:
            return 0

        quantity = int(self._capital_per_trade / signal.entry_price)
        return max(1, quantity)

    def register_trade_opened(self):
        """Register that a new trade has been opened."""
        with self._lock:
            self._open_positions += 1
            self._trade_count_today += 1
            logger.debug(
                f"Trade opened. Open: {self._open_positions}, "
                f"Today's total: {self._trade_count_today}"
            )

    def register_trade_closed(self, pnl: float):
        """
        Register that a trade has been closed.

        Args:
            pnl: Realized P&L for the closed trade.
        """
        with self._lock:
            self._open_positions = max(0, self._open_positions - 1)
            self._daily_realized_pnl += pnl
            logger.debug(
                f"Trade closed. PnL: ₹{pnl:.2f}, "
                f"Daily total: ₹{self._daily_realized_pnl:.2f}, "
                f"Open: {self._open_positions}"
            )

            # Check if loss limit is now breached
            if self._daily_realized_pnl <= -self._max_daily_loss:
                self._kill_switch = True
                logger.warning(
                    f"🛑 DAILY LOSS LIMIT HIT after trade close! "
                    f"Daily P&L: ₹{self._daily_realized_pnl:.2f}"
                )

    def activate_kill_switch(self, reason: str = "Manual activation"):
        """
        Manually activate the kill switch to stop all trading.

        Args:
            reason: Reason for kill switch activation.
        """
        with self._lock:
            self._kill_switch = True
            logger.warning(f"🛑 KILL SWITCH ACTIVATED: {reason}")

    def deactivate_kill_switch(self):
        """Deactivate the kill switch to resume trading."""
        with self._lock:
            self._kill_switch = False
            logger.info("✅ Kill switch deactivated. Trading resumed.")

    @property
    def is_kill_switch_active(self) -> bool:
        return self._kill_switch

    def get_risk_status(self) -> dict:
        """Get current risk management status."""
        with self._lock:
            return {
                "kill_switch": self._kill_switch,
                "daily_pnl": round(self._daily_realized_pnl, 2),
                "max_daily_loss": self._max_daily_loss,
                "pnl_remaining": round(
                    self._max_daily_loss + self._daily_realized_pnl, 2
                ),
                "open_positions": self._open_positions,
                "max_open_positions": self._max_open_positions,
                "trades_today": self._trade_count_today,
                "max_trades_per_day": self._max_trades_per_day,
                "capital_per_trade": self._capital_per_trade,
                "max_position_size": self._max_position_size,
            }

    def set_open_positions_count(self, count: int):
        """Set the open positions count (used during initialization)."""
        with self._lock:
            self._open_positions = count
