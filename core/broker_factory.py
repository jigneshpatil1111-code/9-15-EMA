"""
Broker factory.
Returns the correct broker implementation based on configuration.
"""

import logging

from core.broker_base import BrokerBase
from config.settings import settings

logger = logging.getLogger(__name__)


def get_broker() -> BrokerBase:
    """
    Factory function to create and initialize the appropriate broker instance.
    Reads BROKER setting from configuration and returns the matching implementation.

    Returns:
        Initialized BrokerBase implementation.

    Raises:
        ValueError: If the configured broker is not supported.
        RuntimeError: If broker initialization fails.
    """
    broker_name = settings.BROKER.lower().strip()

    if broker_name == "dhan":
        from core.broker_dhan import DhanBroker

        broker = DhanBroker()
    elif broker_name == "kite":
        raise ValueError(
            "Kite Connect broker is configured but not yet implemented. "
            "Set BROKER=dhan in your .env file."
        )
    elif broker_name == "upstox":
        raise ValueError(
            "Upstox broker is configured but not yet implemented. "
            "Set BROKER=dhan in your .env file."
        )
    else:
        raise ValueError(
            f"Unsupported broker: '{broker_name}'. "
            f"Supported brokers: dhan, kite (future), upstox (future)."
        )

    success = broker.initialize()
    if not success:
        raise RuntimeError(
            f"Failed to initialize broker '{broker_name}'. "
            f"Check your API credentials in the .env file."
        )

    logger.info(f"Broker '{broker_name}' initialized successfully.")
    return broker
