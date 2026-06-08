"""
Telegram message formatters.
Formats trade alerts and reports exactly as specified.
"""

from datetime import datetime
from typing import Dict, Any, Optional

from strategies.base_strategy import Signal


def format_trade_alert(signal: Signal) -> str:
    """
    Format a trade signal as a Telegram alert message.

    Format:
    🚀 LONG TRADE ALERT
    Stock: {symbol}
    Setup: {setup_type}
    Entry: ₹{entry}
    Stop Loss: ₹{stop_loss}
    Target 1: ₹{target1}
    Target 2: ₹{target2}
    Risk Reward: 1:{rr}
    Volume: {volume}
    Signal Score: {score}/100
    Time: {time}
    """
    setup_name = "1% Setup" if signal.setup_type == "1_pct_setup" else "9/15 EMA Pullback"

    timestamp_str = ""
    if isinstance(signal.timestamp, datetime):
        timestamp_str = signal.timestamp.strftime("%H:%M:%S")
    else:
        timestamp_str = str(signal.timestamp)

    volume_formatted = _format_number(signal.volume)

    msg = (
        f"🚀 *LONG TRADE ALERT*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Stock:* `{signal.symbol}`\n"
        f"📋 *Setup:* {setup_name}\n"
        f"💰 *Entry:* ₹{signal.entry_price:.2f}\n"
        f"🛑 *Stop Loss:* ₹{signal.stop_loss:.2f}\n"
        f"🎯 *Target 1:* ₹{signal.target1:.2f}\n"
        f"🎯 *Target 2:* ₹{signal.target2:.2f}\n"
        f"📐 *Risk Reward:* 1:{signal.risk_reward:.1f}\n"
        f"📊 *Volume:* {volume_formatted}\n"
        f"⭐ *Signal Score:* {signal.signal_score:.0f}/100\n"
        f"🕐 *Time:* {timestamp_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    )

    if signal.notes:
        msg += f"📝 _{signal.notes}_\n"

    return msg


def format_exit_alert(signal: Signal) -> str:
    """Format a trade exit notification."""
    exit_reason_map = {
        "target1_hit": "🎯 Target 1 Hit",
        "target2_hit": "🎯🎯 Target 2 Hit",
        "stop_loss": "🛑 Stop Loss Hit",
        "breakeven_timeout": "⏸️ Breakeven Exit (Timeout)",
        "forced_eod_close": "🔔 End of Day Close",
    }

    reason_text = exit_reason_map.get(signal.exit_reason, signal.exit_reason)
    pnl_emoji = "✅" if signal.pnl >= 0 else "❌"
    exit_time_str = signal.exit_time.strftime("%H:%M:%S") if signal.exit_time else "N/A"

    msg = (
        f"📤 *TRADE EXIT*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Stock:* `{signal.symbol}`\n"
        f"💰 *Entry:* ₹{signal.entry_price:.2f}\n"
        f"📤 *Exit:* ₹{signal.exit_price:.2f}\n"
        f"{pnl_emoji} *P&L:* ₹{signal.pnl:+.2f}\n"
        f"📋 *Reason:* {reason_text}\n"
        f"🕐 *Exit Time:* {exit_time_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    )
    return msg


def format_daily_report(stats: Dict[str, Any], report_date: str = "") -> str:
    """
    Format daily performance report.

    📊 DAILY PERFORMANCE REPORT
    Date:
    Total Trades:
    Wins:
    Losses:
    Win Rate:
    Daily P&L:
    Best Trade:
    Worst Trade:
    Average RR:
    """
    pnl = stats.get("total_pnl", 0.0)
    pnl_emoji = "📈" if pnl >= 0 else "📉"

    best = stats.get("best_trade", {})
    worst = stats.get("worst_trade", {})
    best_str = f"{best.get('symbol', 'N/A')} (₹{best.get('pnl', 0):+.2f})" if best else "N/A"
    worst_str = f"{worst.get('symbol', 'N/A')} (₹{worst.get('pnl', 0):+.2f})" if worst else "N/A"

    msg = (
        f"📊 *DAILY PERFORMANCE REPORT*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 *Date:* {report_date}\n"
        f"📊 *Total Trades:* {stats.get('total_trades', 0)}\n"
        f"✅ *Wins:* {stats.get('wins', 0)}\n"
        f"❌ *Losses:* {stats.get('losses', 0)}\n"
        f"📊 *Win Rate:* {stats.get('win_rate', 0.0):.1f}%\n"
        f"{pnl_emoji} *Daily P&L:* ₹{pnl:+.2f}\n"
        f"🏆 *Best Trade:* {best_str}\n"
        f"📉 *Worst Trade:* {worst_str}\n"
        f"📐 *Average RR:* {stats.get('avg_rr', 0.0):.2f}\n"
        f"📊 *Profit Factor:* {stats.get('profit_factor', 0.0):.2f}\n"
        f"📉 *Max Drawdown:* ₹{stats.get('max_drawdown', 0.0):.2f}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    return msg


def format_weekly_report(stats: Dict[str, Any], week_str: str = "") -> str:
    """Format weekly performance report."""
    pnl = stats.get("total_pnl", 0.0)
    pnl_emoji = "📈" if pnl >= 0 else "📉"

    best = stats.get("best_trade", {})
    worst = stats.get("worst_trade", {})
    best_str = f"{best.get('symbol', 'N/A')} (₹{best.get('pnl', 0):+.2f})" if best else "N/A"
    worst_str = f"{worst.get('symbol', 'N/A')} (₹{worst.get('pnl', 0):+.2f})" if worst else "N/A"

    msg = (
        f"📊 *WEEKLY PERFORMANCE REPORT*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 *Week:* {week_str}\n"
        f"📊 *Total Trades:* {stats.get('total_trades', 0)}\n"
        f"✅ *Wins:* {stats.get('wins', 0)}\n"
        f"❌ *Losses:* {stats.get('losses', 0)}\n"
        f"📊 *Win Rate:* {stats.get('win_rate', 0.0):.1f}%\n"
        f"{pnl_emoji} *Weekly P&L:* ₹{pnl:+.2f}\n"
        f"📉 *Weekly Drawdown:* ₹{stats.get('max_drawdown', 0.0):.2f}\n"
        f"🏆 *Best Trade:* {best_str}\n"
        f"📉 *Worst Trade:* {worst_str}\n"
        f"📊 *Profit Factor:* {stats.get('profit_factor', 0.0):.2f}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    return msg


def format_monthly_report(
    stats: Dict[str, Any],
    month_str: str = "",
    top_stocks: list = None,
    worst_stocks: list = None,
) -> str:
    """Format monthly performance report."""
    pnl = stats.get("total_pnl", 0.0)
    pnl_emoji = "📈" if pnl >= 0 else "📉"

    msg = (
        f"📊 *MONTHLY PERFORMANCE REPORT*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 *Month:* {month_str}\n"
        f"{pnl_emoji} *Monthly P&L:* ₹{pnl:+.2f}\n"
        f"📊 *Win Rate:* {stats.get('win_rate', 0.0):.1f}%\n"
        f"📊 *Total Trades:* {stats.get('total_trades', 0)}\n"
        f"📉 *Max Drawdown:* ₹{stats.get('max_drawdown', 0.0):.2f}\n"
        f"📊 *Profit Factor:* {stats.get('profit_factor', 0.0):.2f}\n"
    )

    if top_stocks:
        msg += "\n🏆 *Top Performing Stocks:*\n"
        for i, s in enumerate(top_stocks[:5], 1):
            msg += f"  {i}. {s['symbol']}: ₹{s['total_pnl']:+.2f}\n"

    if worst_stocks:
        msg += "\n📉 *Worst Performing Stocks:*\n"
        for i, s in enumerate(worst_stocks[:5], 1):
            msg += f"  {i}. {s['symbol']}: ₹{s['total_pnl']:+.2f}\n"

    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    return msg


def format_yearly_report(stats: Dict[str, Any], year: int = 0) -> str:
    """Format yearly performance report."""
    pnl = stats.get("total_pnl", 0.0)
    pnl_emoji = "📈" if pnl >= 0 else "📉"

    msg = (
        f"📊 *YEARLY PERFORMANCE REPORT*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 *Year:* {year}\n"
        f"{pnl_emoji} *Yearly P&L:* ₹{pnl:+.2f}\n"
        f"📊 *Win Rate:* {stats.get('win_rate', 0.0):.1f}%\n"
        f"📊 *Total Trades:* {stats.get('total_trades', 0)}\n"
        f"📉 *Annual Drawdown:* ₹{stats.get('max_drawdown', 0.0):.2f}\n"
        f"📊 *Profit Factor:* {stats.get('profit_factor', 0.0):.2f}\n"
        f"📐 *Average RR:* {stats.get('avg_rr', 0.0):.2f}\n"
        f"🏆 *Largest Winner:* ₹{stats.get('largest_winner', 0.0):+.2f}\n"
        f"📉 *Largest Loser:* ₹{stats.get('largest_loser', 0.0):+.2f}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    )
    return msg


def format_sentiment_update(sentiment_data) -> str:
    """Format a market sentiment update message."""
    status_emoji = "🟢" if sentiment_data.status == "BULLISH" else "🟡"

    msg = (
        f"{status_emoji} *Market Sentiment: {sentiment_data.status}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📈 Positive: {sentiment_data.positive_count}\n"
        f"📉 Negative: {sentiment_data.negative_count}\n"
        f"📊 Total Scanned: {sentiment_data.total_scanned}\n"
        f"🕐 Time: {sentiment_data.timestamp.strftime('%H:%M:%S')}\n"
    )
    return msg


def _format_number(num: int) -> str:
    """Format a large number with commas."""
    if num >= 10_000_000:
        return f"{num / 10_000_000:.2f} Cr"
    elif num >= 100_000:
        return f"{num / 100_000:.2f} L"
    elif num >= 1_000:
        return f"{num:,}"
    return str(num)
