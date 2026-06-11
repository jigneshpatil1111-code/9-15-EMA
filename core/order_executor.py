"""
Order Executor Module.
Handles actual order placement via Dhan API or simulated paper trading.

Supports:
- Regular intraday orders (MARKET / LIMIT)
- Super Orders (Entry + Stop Loss + Target in one call)
- Paper trading mode (simulated orders for testing)
- Order status tracking
- Position management
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum

import pytz

from config.settings import settings

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")


class OrderStatus(Enum):
    PENDING = "PENDING"
    PLACED = "PLACED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    FILLED = "FILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    PAPER = "PAPER"  # Paper trading simulated order


class TransactionType(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class ProductType(Enum):
    INTRADAY = "INTRADAY"
    CNC = "CNC"
    MARGIN = "MARGIN"


@dataclass
class OrderResult:
    """Result of an order placement attempt."""
    success: bool
    order_id: str = ""
    status: OrderStatus = OrderStatus.PENDING
    message: str = ""
    security_id: str = ""
    symbol: str = ""
    transaction_type: str = ""
    quantity: int = 0
    price: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(IST))
    is_paper: bool = False

    # Super order specific
    target_order_id: str = ""
    sl_order_id: str = ""


class OrderExecutor:
    """
    Executes trading orders via Dhan API or simulates them in paper mode.

    Paper Trading Mode:
    - When PAPER_TRADING=true, orders are simulated (logged but not sent to exchange)
    - All order lifecycle events are tracked in memory
    - Telegram alerts indicate [PAPER] mode
    - Perfect for testing strategy logic before going live

    Live Trading Mode:
    - When PAPER_TRADING=false, orders are placed via Dhan API
    - Requires Static IP whitelisting on Dhan Developer Console
    - Super Orders recommended for automatic SL/Target management
    """

    def __init__(self, paper_trading: bool = True):
        self._paper_trading = paper_trading
        self._dhan_client = None
        self._orders: Dict[str, OrderResult] = {}  # order_id -> OrderResult
        self._rate_limit_delay = 0.35
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize the order executor."""
        if self._paper_trading:
            logger.info("📝 Order Executor initialized in PAPER TRADING mode.")
            logger.info("   Orders will be simulated — no real money will be used.")
            self._initialized = True
            return True

        # Live mode — initialize Dhan client
        try:
            from dhanhq import DhanContext, dhanhq

            context = DhanContext(settings.DHAN_CLIENT_ID, settings.DHAN_ACCESS_TOKEN)
            self._dhan_client = dhanhq(context)
            self._initialized = True
            logger.info("💰 Order Executor initialized in LIVE TRADING mode.")
            logger.warning("   ⚠️  REAL ORDERS WILL BE PLACED. Ensure Static IP is whitelisted.")
            return True
        except ImportError:
            logger.error("dhanhq package not installed. Run: pip install dhanhq")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Order Executor: {e}")
            return False

    @property
    def is_paper_trading(self) -> bool:
        return self._paper_trading

    def _throttle(self):
        """Rate-limit API calls."""
        time.sleep(self._rate_limit_delay)

    # ── Paper Trading Helpers ──────────────────────────────────────

    def _generate_paper_order_id(self) -> str:
        """Generate a unique paper order ID."""
        return f"PAPER-{uuid.uuid4().hex[:8].upper()}"

    def _simulate_order(
        self,
        security_id: str,
        symbol: str,
        transaction_type: str,
        quantity: int,
        price: float,
        order_type: str = "MARKET",
    ) -> OrderResult:
        """Simulate a paper trading order."""
        order_id = self._generate_paper_order_id()
        result = OrderResult(
            success=True,
            order_id=order_id,
            status=OrderStatus.PAPER,
            message=f"[PAPER] {transaction_type} {quantity} x {symbol} @ ₹{price:.2f}",
            security_id=security_id,
            symbol=symbol,
            transaction_type=transaction_type,
            quantity=quantity,
            price=price,
            is_paper=True,
        )
        self._orders[order_id] = result
        logger.info(
            f"📝 [PAPER ORDER] {transaction_type} {quantity} x {symbol} "
            f"@ ₹{price:.2f} | Order ID: {order_id}"
        )
        return result

    # ── Order Placement Methods ────────────────────────────────────

    def place_intraday_buy(
        self,
        security_id: str,
        symbol: str,
        quantity: int,
        price: float,
        order_type: str = "LIMIT",
        exchange_segment: str = "NSE_EQ",
    ) -> OrderResult:
        """
        Place an intraday BUY order.

        Args:
            security_id: Dhan security ID.
            symbol: Trading symbol (for logging).
            quantity: Number of shares.
            price: Limit price (ignored for MARKET orders).
            order_type: 'MARKET' or 'LIMIT'.
            exchange_segment: Exchange segment.

        Returns:
            OrderResult with order details and status.
        """
        if not self._initialized:
            return OrderResult(
                success=False, message="Order Executor not initialized."
            )

        # Paper trading
        if self._paper_trading:
            return self._simulate_order(
                security_id, symbol, "BUY", quantity, price, order_type
            )

        # Live trading
        self._throttle()
        try:
            params = {
                "security_id": security_id,
                "exchange_segment": exchange_segment,
                "transaction_type": "BUY",
                "quantity": quantity,
                "order_type": order_type,
                "product_type": "INTRADAY",
            }
            if order_type == "LIMIT":
                params["price"] = price

            response = self._dhan_client.place_order(**params)

            if response and response.get("status") == "success":
                order_id = str(response.get("data", {}).get("orderId", ""))
                result = OrderResult(
                    success=True,
                    order_id=order_id,
                    status=OrderStatus.PLACED,
                    message=f"BUY order placed: {quantity} x {symbol} @ ₹{price:.2f}",
                    security_id=security_id,
                    symbol=symbol,
                    transaction_type="BUY",
                    quantity=quantity,
                    price=price,
                )
                self._orders[order_id] = result
                logger.info(
                    f"✅ BUY ORDER PLACED: {quantity} x {symbol} @ ₹{price:.2f} "
                    f"| Order ID: {order_id}"
                )
                return result
            else:
                error_msg = response.get("remarks", {}).get("error_message", str(response)) if response else "No response"
                logger.error(f"❌ BUY order failed for {symbol}: {error_msg}")
                return OrderResult(
                    success=False,
                    status=OrderStatus.REJECTED,
                    message=f"Order rejected: {error_msg}",
                    security_id=security_id,
                    symbol=symbol,
                )

        except Exception as e:
            logger.error(f"❌ BUY order error for {symbol}: {e}")
            return OrderResult(
                success=False,
                message=f"Order error: {str(e)}",
                security_id=security_id,
                symbol=symbol,
            )

    def place_intraday_sell(
        self,
        security_id: str,
        symbol: str,
        quantity: int,
        price: float,
        order_type: str = "MARKET",
        exchange_segment: str = "NSE_EQ",
    ) -> OrderResult:
        """
        Place an intraday SELL order (for exiting a position).

        Args:
            security_id: Dhan security ID.
            symbol: Trading symbol.
            quantity: Number of shares to sell.
            price: Limit price (ignored for MARKET orders).
            order_type: 'MARKET' or 'LIMIT'.
            exchange_segment: Exchange segment.

        Returns:
            OrderResult with order details and status.
        """
        if not self._initialized:
            return OrderResult(
                success=False, message="Order Executor not initialized."
            )

        # Paper trading
        if self._paper_trading:
            return self._simulate_order(
                security_id, symbol, "SELL", quantity, price, order_type
            )

        # Live trading
        self._throttle()
        try:
            params = {
                "security_id": security_id,
                "exchange_segment": exchange_segment,
                "transaction_type": "SELL",
                "quantity": quantity,
                "order_type": order_type,
                "product_type": "INTRADAY",
            }
            if order_type == "LIMIT":
                params["price"] = price

            response = self._dhan_client.place_order(**params)

            if response and response.get("status") == "success":
                order_id = str(response.get("data", {}).get("orderId", ""))
                result = OrderResult(
                    success=True,
                    order_id=order_id,
                    status=OrderStatus.PLACED,
                    message=f"SELL order placed: {quantity} x {symbol} @ ₹{price:.2f}",
                    security_id=security_id,
                    symbol=symbol,
                    transaction_type="SELL",
                    quantity=quantity,
                    price=price,
                )
                self._orders[order_id] = result
                logger.info(
                    f"✅ SELL ORDER PLACED: {quantity} x {symbol} @ ₹{price:.2f} "
                    f"| Order ID: {order_id}"
                )
                return result
            else:
                error_msg = response.get("remarks", {}).get("error_message", str(response)) if response else "No response"
                logger.error(f"❌ SELL order failed for {symbol}: {error_msg}")
                return OrderResult(
                    success=False,
                    status=OrderStatus.REJECTED,
                    message=f"Order rejected: {error_msg}",
                    security_id=security_id,
                    symbol=symbol,
                )

        except Exception as e:
            logger.error(f"❌ SELL order error for {symbol}: {e}")
            return OrderResult(
                success=False,
                message=f"Order error: {str(e)}",
                security_id=security_id,
                symbol=symbol,
            )

    def place_super_order(
        self,
        security_id: str,
        symbol: str,
        quantity: int,
        entry_price: float,
        stop_loss_price: float,
        target_price: float,
        order_type: str = "LIMIT",
        exchange_segment: str = "NSE_EQ",
        trailing_jump: float = 0.0,
    ) -> OrderResult:
        """
        Place a Super Order: Entry + Stop Loss + Target in one call.
        This is the BEST option for the 1% Setup and EMA Pullback strategies
        because the SL and Target are managed automatically by the exchange.

        Args:
            security_id: Dhan security ID.
            symbol: Trading symbol.
            quantity: Number of shares.
            entry_price: Entry limit price.
            stop_loss_price: Stop loss price.
            target_price: Target price.
            order_type: 'MARKET' or 'LIMIT'.
            exchange_segment: Exchange segment.
            trailing_jump: Trailing stop jump (0 = no trailing).

        Returns:
            OrderResult with order details.
        """
        if not self._initialized:
            return OrderResult(
                success=False, message="Order Executor not initialized."
            )

        # Paper trading
        if self._paper_trading:
            order_id = self._generate_paper_order_id()
            sl_id = self._generate_paper_order_id()
            tgt_id = self._generate_paper_order_id()
            result = OrderResult(
                success=True,
                order_id=order_id,
                status=OrderStatus.PAPER,
                message=(
                    f"[PAPER SUPER ORDER] BUY {quantity} x {symbol} "
                    f"@ ₹{entry_price:.2f} | SL: ₹{stop_loss_price:.2f} "
                    f"| Target: ₹{target_price:.2f}"
                ),
                security_id=security_id,
                symbol=symbol,
                transaction_type="BUY",
                quantity=quantity,
                price=entry_price,
                is_paper=True,
                sl_order_id=sl_id,
                target_order_id=tgt_id,
            )
            self._orders[order_id] = result
            logger.info(
                f"📝 [PAPER SUPER ORDER] BUY {quantity} x {symbol} "
                f"@ ₹{entry_price:.2f} | SL: ₹{stop_loss_price:.2f} "
                f"| Target: ₹{target_price:.2f} | Order ID: {order_id}"
            )
            return result

        # Live trading — Super Order
        self._throttle()
        try:
            params = {
                "security_id": security_id,
                "exchange_segment": exchange_segment,
                "transaction_type": "BUY",
                "quantity": quantity,
                "order_type": order_type,
                "price": entry_price,
                "target_price": target_price,
                "stop_loss_price": stop_loss_price,
            }
            if trailing_jump > 0:
                params["trailing_jump"] = trailing_jump

            response = self._dhan_client.place_super_order(**params)

            if response and response.get("status") == "success":
                data = response.get("data", {})
                order_id = str(data.get("orderId", ""))
                result = OrderResult(
                    success=True,
                    order_id=order_id,
                    status=OrderStatus.PLACED,
                    message=(
                        f"SUPER ORDER placed: BUY {quantity} x {symbol} "
                        f"@ ₹{entry_price:.2f} | SL: ₹{stop_loss_price:.2f} "
                        f"| Target: ₹{target_price:.2f}"
                    ),
                    security_id=security_id,
                    symbol=symbol,
                    transaction_type="BUY",
                    quantity=quantity,
                    price=entry_price,
                    sl_order_id=str(data.get("slOrderId", "")),
                    target_order_id=str(data.get("targetOrderId", "")),
                )
                self._orders[order_id] = result
                logger.info(
                    f"✅ SUPER ORDER PLACED: BUY {quantity} x {symbol} "
                    f"@ ₹{entry_price:.2f} | SL: ₹{stop_loss_price:.2f} "
                    f"| Target: ₹{target_price:.2f} | Order ID: {order_id}"
                )
                return result
            else:
                error_msg = response.get("remarks", {}).get("error_message", str(response)) if response else "No response"
                logger.error(f"❌ Super order failed for {symbol}: {error_msg}")
                return OrderResult(
                    success=False,
                    status=OrderStatus.REJECTED,
                    message=f"Super order rejected: {error_msg}",
                    security_id=security_id,
                    symbol=symbol,
                )

        except Exception as e:
            logger.error(f"❌ Super order error for {symbol}: {e}")
            return OrderResult(
                success=False,
                message=f"Super order error: {str(e)}",
                security_id=security_id,
                symbol=symbol,
            )

    def cancel_order(self, order_id: str) -> OrderResult:
        """Cancel an existing order."""
        if self._paper_trading:
            if order_id in self._orders:
                self._orders[order_id].status = OrderStatus.CANCELLED
                logger.info(f"📝 [PAPER] Order {order_id} cancelled.")
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    status=OrderStatus.CANCELLED,
                    message=f"[PAPER] Order cancelled: {order_id}",
                    is_paper=True,
                )
            return OrderResult(
                success=False,
                message=f"Paper order not found: {order_id}",
            )

        # Live cancel
        self._throttle()
        try:
            response = self._dhan_client.cancel_order(order_id)
            if response and response.get("status") == "success":
                if order_id in self._orders:
                    self._orders[order_id].status = OrderStatus.CANCELLED
                logger.info(f"✅ Order cancelled: {order_id}")
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    status=OrderStatus.CANCELLED,
                    message=f"Order cancelled: {order_id}",
                )
            else:
                error_msg = str(response)
                logger.error(f"❌ Cancel failed for {order_id}: {error_msg}")
                return OrderResult(
                    success=False,
                    message=f"Cancel failed: {error_msg}",
                )
        except Exception as e:
            logger.error(f"❌ Cancel error for {order_id}: {e}")
            return OrderResult(success=False, message=f"Cancel error: {str(e)}")

    def get_order_status(self, order_id: str) -> OrderResult:
        """Get the current status of an order."""
        if self._paper_trading:
            return self._orders.get(
                order_id,
                OrderResult(success=False, message=f"Paper order not found: {order_id}"),
            )

        self._throttle()
        try:
            response = self._dhan_client.get_order_by_id(order_id)
            if response and response.get("status") == "success":
                data = response.get("data", {})
                status_str = data.get("orderStatus", "UNKNOWN")
                status_map = {
                    "PENDING": OrderStatus.PENDING,
                    "TRADED": OrderStatus.FILLED,
                    "TRANSIT": OrderStatus.PLACED,
                    "REJECTED": OrderStatus.REJECTED,
                    "CANCELLED": OrderStatus.CANCELLED,
                    "PART_TRADED": OrderStatus.PARTIALLY_FILLED,
                }
                return OrderResult(
                    success=True,
                    order_id=order_id,
                    status=status_map.get(status_str, OrderStatus.PENDING),
                    message=f"Order status: {status_str}",
                    price=float(data.get("price", 0)),
                    quantity=int(data.get("quantity", 0)),
                )
            return OrderResult(
                success=False,
                message=f"Failed to fetch order status: {response}",
            )
        except Exception as e:
            logger.error(f"Order status error for {order_id}: {e}")
            return OrderResult(success=False, message=f"Status error: {str(e)}")

    def get_positions(self) -> List[Dict]:
        """Get all current positions."""
        if self._paper_trading:
            # Return paper positions from order tracking
            positions = []
            for oid, order in self._orders.items():
                if order.status in (OrderStatus.PAPER, OrderStatus.FILLED):
                    positions.append({
                        "order_id": order.order_id,
                        "symbol": order.symbol,
                        "security_id": order.security_id,
                        "quantity": order.quantity,
                        "price": order.price,
                        "type": order.transaction_type,
                        "is_paper": True,
                    })
            return positions

        self._throttle()
        try:
            response = self._dhan_client.get_positions()
            if response and response.get("status") == "success":
                return response.get("data", [])
            return []
        except Exception as e:
            logger.error(f"Positions fetch error: {e}")
            return []

    def get_all_orders(self) -> Dict[str, OrderResult]:
        """Get all tracked orders."""
        return dict(self._orders)

    def get_today_order_count(self) -> int:
        """Get the number of orders placed today."""
        today = datetime.now(IST).date()
        count = 0
        for order in self._orders.values():
            if order.timestamp.date() == today:
                count += 1
        return count
