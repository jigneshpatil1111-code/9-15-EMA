"""
Telegram notification sender.
Sends trade alerts and reports to a configured Telegram chat.
"""

import logging
import time
from typing import Optional

import requests

from strategies.base_strategy import Signal
from telegram_bot.formatters import (
    format_trade_alert,
    format_exit_alert,
    format_sentiment_update,
)
from config.settings import settings

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """
    Sends messages to Telegram using the Bot API.
    Uses direct HTTP requests for reliability (no async dependency).
    """

    BASE_URL = "https://api.telegram.org/bot{token}"

    def __init__(self, bot_token: str = "", chat_id: str = ""):
        self._bot_token = bot_token or settings.TELEGRAM_BOT_TOKEN
        self._chat_id = chat_id or settings.TELEGRAM_CHAT_ID
        self._base_url = self.BASE_URL.format(token=self._bot_token)
        self._max_retries = 3
        self._retry_delay = 2  # seconds

    def _send_message(
        self,
        text: str,
        parse_mode: str = "Markdown",
        disable_preview: bool = True,
    ) -> bool:
        """
        Send a message to the configured Telegram chat.

        Args:
            text: Message text (supports Markdown formatting).
            parse_mode: 'Markdown' or 'HTML'.
            disable_preview: Disable link preview.

        Returns:
            True if message was sent successfully.
        """
        if not self._bot_token or not self._chat_id:
            logger.warning("Telegram credentials not configured. Skipping send.")
            return False

        url = f"{self._base_url}/sendMessage"
        payload = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_preview,
        }

        for attempt in range(1, self._max_retries + 1):
            try:
                response = requests.post(url, json=payload, timeout=10)
                data = response.json()

                if data.get("ok"):
                    logger.debug(f"Telegram message sent successfully.")
                    return True
                else:
                    error_desc = data.get("description", "Unknown error")
                    logger.warning(
                        f"Telegram API error (attempt {attempt}): {error_desc}"
                    )

                    # If message is too long, try splitting
                    if "message is too long" in error_desc.lower():
                        return self._send_long_message(text, parse_mode)

            except requests.exceptions.Timeout:
                logger.warning(f"Telegram request timeout (attempt {attempt})")
            except requests.exceptions.ConnectionError:
                logger.warning(f"Telegram connection error (attempt {attempt})")
            except Exception as e:
                logger.error(f"Telegram send error (attempt {attempt}): {e}")

            if attempt < self._max_retries:
                time.sleep(self._retry_delay * attempt)

        logger.error("Failed to send Telegram message after all retries.")
        return False

    def _send_long_message(
        self, text: str, parse_mode: str = "Markdown"
    ) -> bool:
        """
        Send a long message by splitting into chunks.
        Telegram has a 4096 character limit per message.
        """
        max_length = 4000
        chunks = []
        current = ""

        for line in text.split("\n"):
            if len(current) + len(line) + 1 > max_length:
                chunks.append(current)
                current = line
            else:
                current = current + "\n" + line if current else line

        if current:
            chunks.append(current)

        success = True
        for i, chunk in enumerate(chunks):
            if not self._send_message(chunk, parse_mode):
                success = False
            if i < len(chunks) - 1:
                time.sleep(0.5)  # Small delay between chunks

        return success

    def send_trade_alert(self, signal: Signal) -> bool:
        """Send a formatted trade alert to Telegram."""
        msg = format_trade_alert(signal)
        logger.info(f"Sending trade alert for {signal.symbol}")
        return self._send_message(msg)

    def send_exit_alert(self, signal: Signal) -> bool:
        """Send a trade exit notification to Telegram."""
        msg = format_exit_alert(signal)
        logger.info(f"Sending exit alert for {signal.symbol}")
        return self._send_message(msg)

    def send_report(self, report_text: str) -> bool:
        """Send a formatted report to Telegram."""
        logger.info("Sending report to Telegram.")
        return self._send_message(report_text)

    def send_sentiment_update(self, sentiment_data) -> bool:
        """Send a market sentiment update to Telegram."""
        msg = format_sentiment_update(sentiment_data)
        return self._send_message(msg)

    def send_custom_message(self, message: str) -> bool:
        """Send a custom message to Telegram."""
        return self._send_message(message)

    def test_connection(self) -> bool:
        """
        Test the Telegram bot connection by sending a test message.
        Returns True if the message was delivered.
        """
        test_msg = (
            "🤖 *Intraday Scanner Bot*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "✅ Connection test successful!\n"
            "Bot is online and ready to send alerts.\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        return self._send_message(test_msg)
