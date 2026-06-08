"""
KPI metric display cards for the dashboard.
"""

import streamlit as st


def metric_card(label: str, value: str, delta: str = "", delta_color: str = "normal"):
    """
    Display a styled KPI metric card.

    Args:
        label: Metric label.
        value: Metric value string.
        delta: Delta value string (optional).
        delta_color: 'normal', 'inverse', or 'off'.
    """
    st.metric(label=label, value=value, delta=delta, delta_color=delta_color)


def pnl_card(label: str, pnl: float):
    """Display a P&L metric card with color-coded delta."""
    color = "normal" if pnl >= 0 else "inverse"
    delta_str = f"₹{pnl:+,.2f}"
    st.metric(
        label=label,
        value=f"₹{pnl:,.2f}",
        delta=delta_str,
        delta_color=color,
    )


def stat_card(label: str, value: str, icon: str = ""):
    """Display a simple stat card with optional icon."""
    display_label = f"{icon} {label}" if icon else label
    st.metric(label=display_label, value=value)


def render_kpi_row(stats: dict):
    """Render a row of key performance indicators."""
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        pnl_card("Today's P&L", stats.get("total_pnl", 0.0))

    with col2:
        stat_card("Total Trades", str(stats.get("total_trades", 0)), "📊")

    with col3:
        stat_card("Win Rate", f"{stats.get('win_rate', 0.0):.1f}%", "🎯")

    with col4:
        stat_card("Avg RR", f"{stats.get('avg_rr', 0.0):.2f}", "📐")

    with col5:
        stat_card(
            "Open Trades",
            str(stats.get("open_count", 0)),
            "📈",
        )


def render_performance_kpis(stats: dict):
    """Render comprehensive performance KPIs."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        pnl_card("Total P&L", stats.get("total_pnl", 0.0))
        stat_card("Win Rate", f"{stats.get('win_rate', 0.0):.1f}%", "🎯")

    with col2:
        stat_card("Total Trades", str(stats.get("total_trades", 0)), "📊")
        stat_card("Profit Factor", f"{stats.get('profit_factor', 0.0):.2f}", "📊")

    with col3:
        stat_card("Wins / Losses", f"{stats.get('wins', 0)} / {stats.get('losses', 0)}", "✅")
        pnl_card("Max Drawdown", -abs(stats.get("max_drawdown", 0.0)))

    with col4:
        pnl_card("Largest Winner", stats.get("largest_winner", 0.0))
        pnl_card("Largest Loser", stats.get("largest_loser", 0.0))


def status_badge(text: str, status: str = "info"):
    """Render a colored status badge."""
    colors = {
        "success": "#00d26a",
        "warning": "#ffd700",
        "danger": "#ff4757",
        "info": "#1e90ff",
    }
    color = colors.get(status, colors["info"])

    st.markdown(
        f'<span style="background-color: {color}; color: white; '
        f'padding: 4px 12px; border-radius: 12px; font-size: 14px; '
        f'font-weight: 600;">{text}</span>',
        unsafe_allow_html=True,
    )
