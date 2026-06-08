"""
Plotly chart components for the dashboard.
"""

import plotly.graph_objects as go
import plotly.express as px
from typing import List, Dict, Any
import pandas as pd


CHART_THEME = {
    "bg_color": "#0e1117",
    "paper_color": "#0e1117",
    "grid_color": "#1e2430",
    "text_color": "#fafafa",
    "green": "#00d26a",
    "red": "#ff4757",
    "blue": "#1e90ff",
    "gold": "#ffd700",
    "purple": "#a855f7",
    "cyan": "#06b6d4",
}


def create_equity_curve(data: List[Dict]) -> go.Figure:
    """Create an equity curve chart from daily P&L data."""
    if not data:
        fig = go.Figure()
        fig.update_layout(
            title="Equity Curve",
            template="plotly_dark",
        )
        return fig

    df = pd.DataFrame(data)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["cumulative_pnl"],
            mode="lines",
            name="Cumulative P&L",
            line=dict(color=CHART_THEME["cyan"], width=2),
            fill="tozeroy",
            fillcolor="rgba(6, 182, 212, 0.1)",
        )
    )

    fig.update_layout(
        title="📈 Equity Curve",
        xaxis_title="Date",
        yaxis_title="Cumulative P&L (₹)",
        template="plotly_dark",
        paper_bgcolor=CHART_THEME["paper_color"],
        plot_bgcolor=CHART_THEME["bg_color"],
        font=dict(color=CHART_THEME["text_color"], family="Inter"),
        height=400,
        margin=dict(l=20, r=20, t=50, b=20),
    )

    return fig


def create_drawdown_chart(data: List[Dict]) -> go.Figure:
    """Create a drawdown chart."""
    if not data:
        fig = go.Figure()
        fig.update_layout(title="Drawdown", template="plotly_dark")
        return fig

    df = pd.DataFrame(data)

    # Calculate drawdown
    cumulative = df["cumulative_pnl"].values
    peak = pd.Series(cumulative).cummax()
    drawdown = cumulative - peak

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=drawdown,
            mode="lines",
            name="Drawdown",
            line=dict(color=CHART_THEME["red"], width=2),
            fill="tozeroy",
            fillcolor="rgba(255, 71, 87, 0.15)",
        )
    )

    fig.update_layout(
        title="📉 Drawdown Analysis",
        xaxis_title="Date",
        yaxis_title="Drawdown (₹)",
        template="plotly_dark",
        paper_bgcolor=CHART_THEME["paper_color"],
        plot_bgcolor=CHART_THEME["bg_color"],
        font=dict(color=CHART_THEME["text_color"], family="Inter"),
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
    )

    return fig


def create_pnl_bar_chart(data: List[Dict]) -> go.Figure:
    """Create a daily P&L bar chart."""
    if not data:
        fig = go.Figure()
        fig.update_layout(title="Daily P&L", template="plotly_dark")
        return fig

    df = pd.DataFrame(data)

    # Auto-detect column name
    pnl_col = "pnl" if "pnl" in df.columns else "daily_pnl"

    colors = [
        CHART_THEME["green"] if p >= 0 else CHART_THEME["red"]
        for p in df[pnl_col]
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["date"],
            y=df[pnl_col],
            marker_color=colors,
            name="Daily P&L",
        )
    )

    fig.update_layout(
        title="📊 Daily P&L",
        xaxis_title="Date",
        yaxis_title="P&L (₹)",
        template="plotly_dark",
        paper_bgcolor=CHART_THEME["paper_color"],
        plot_bgcolor=CHART_THEME["bg_color"],
        font=dict(color=CHART_THEME["text_color"], family="Inter"),
        height=350,
        margin=dict(l=20, r=20, t=50, b=20),
    )

    return fig


def create_win_rate_pie(wins: int, losses: int, breakeven: int = 0) -> go.Figure:
    """Create a win rate pie chart."""
    labels = ["Wins", "Losses"]
    values = [wins, losses]
    colors = [CHART_THEME["green"], CHART_THEME["red"]]

    if breakeven > 0:
        labels.append("Breakeven")
        values.append(breakeven)
        colors.append(CHART_THEME["gold"])

    fig = go.Figure()
    fig.add_trace(
        go.Pie(
            labels=labels,
            values=values,
            marker=dict(colors=colors),
            hole=0.5,
            textinfo="label+percent",
            textfont=dict(color="white"),
        )
    )

    fig.update_layout(
        title="📊 Win Rate",
        template="plotly_dark",
        paper_bgcolor=CHART_THEME["paper_color"],
        font=dict(color=CHART_THEME["text_color"], family="Inter"),
        height=300,
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=False,
    )

    return fig


def create_setup_comparison(setup_data: Dict[str, Dict]) -> go.Figure:
    """Create a comparison chart between strategy setups."""
    setups = list(setup_data.keys())
    setup_labels = [
        "1% Setup" if s == "1_pct_setup" else "EMA Pullback"
        for s in setups
    ]

    wins = [setup_data[s].get("wins", 0) for s in setups]
    losses = [setup_data[s].get("losses", 0) for s in setups]
    pnl = [setup_data[s].get("total_pnl", 0) for s in setups]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Wins", x=setup_labels, y=wins, marker_color=CHART_THEME["green"]))
    fig.add_trace(go.Bar(name="Losses", x=setup_labels, y=losses, marker_color=CHART_THEME["red"]))

    fig.update_layout(
        title="📊 Setup Comparison",
        barmode="group",
        template="plotly_dark",
        paper_bgcolor=CHART_THEME["paper_color"],
        plot_bgcolor=CHART_THEME["bg_color"],
        font=dict(color=CHART_THEME["text_color"], family="Inter"),
        height=350,
        margin=dict(l=20, r=20, t=50, b=20),
    )

    return fig


def create_sentiment_gauge(positive: int, total: int, threshold: int = 300) -> go.Figure:
    """Create a sentiment gauge chart."""
    fig = go.Figure()

    fig.add_trace(
        go.Indicator(
            mode="gauge+number+delta",
            value=positive,
            title={"text": "Bullish Stocks", "font": {"size": 16, "color": "white"}},
            delta={"reference": threshold, "increasing": {"color": CHART_THEME["green"]}},
            gauge={
                "axis": {"range": [0, total if total > 0 else 500], "tickcolor": "white"},
                "bar": {"color": CHART_THEME["cyan"]},
                "bgcolor": CHART_THEME["bg_color"],
                "borderwidth": 2,
                "bordercolor": "#2d3748",
                "steps": [
                    {"range": [0, threshold], "color": "rgba(255, 71, 87, 0.2)"},
                    {"range": [threshold, total if total > 0 else 500], "color": "rgba(0, 210, 106, 0.2)"},
                ],
                "threshold": {
                    "line": {"color": CHART_THEME["gold"], "width": 3},
                    "thickness": 0.8,
                    "value": threshold,
                },
            },
        )
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=CHART_THEME["paper_color"],
        font=dict(color=CHART_THEME["text_color"], family="Inter"),
        height=250,
        margin=dict(l=30, r=30, t=30, b=10),
    )

    return fig


def create_monthly_heatmap(monthly_data: Dict[str, float]) -> go.Figure:
    """Create a monthly returns heatmap."""
    if not monthly_data:
        fig = go.Figure()
        fig.update_layout(title="Monthly Returns", template="plotly_dark")
        return fig

    months = list(monthly_data.keys())
    values = list(monthly_data.values())

    colors = [
        CHART_THEME["green"] if v >= 0 else CHART_THEME["red"]
        for v in values
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=months,
            y=values,
            marker_color=colors,
            text=[f"₹{v:,.0f}" for v in values],
            textposition="outside",
        )
    )

    fig.update_layout(
        title="📊 Monthly Returns",
        xaxis_title="Month",
        yaxis_title="P&L (₹)",
        template="plotly_dark",
        paper_bgcolor=CHART_THEME["paper_color"],
        plot_bgcolor=CHART_THEME["bg_color"],
        font=dict(color=CHART_THEME["text_color"], family="Inter"),
        height=350,
        margin=dict(l=20, r=20, t=50, b=20),
    )

    return fig
