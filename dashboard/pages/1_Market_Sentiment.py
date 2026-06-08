"""Market Sentiment page."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from datetime import date, datetime

st.set_page_config(page_title="Market Sentiment", page_icon="🌡️", layout="wide")
st.title("🌡️ Market Sentiment")
st.markdown("*Nifty 500 breadth analysis — scanning requires ≥300 positive stocks*")

try:
    from database.trade_repository import TradeRepository
    from dashboard.components.charts import create_sentiment_gauge

    repo = TradeRepository()

    # Try to load latest sentiment from a shared state file
    sentiment_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "sentiment_state.json")

    positive = 0
    negative = 0
    total = 500
    status = "NEUTRAL"

    if os.path.exists(sentiment_file):
        import json
        with open(sentiment_file) as f:
            sentiment = json.load(f)
        positive = sentiment.get("positive_count", 0)
        negative = sentiment.get("negative_count", 0)
        total = sentiment.get("total_scanned", 500)
        status = sentiment.get("status", "NEUTRAL")

    # Status display
    col1, col2, col3 = st.columns(3)
    with col1:
        if status == "BULLISH":
            st.markdown('<p class="status-bullish">🟢 BULLISH — Scanning Active</p>', unsafe_allow_html=True)
        else:
            st.markdown('<p class="status-neutral">🟡 NEUTRAL — Scanning Paused</p>', unsafe_allow_html=True)

    with col2:
        st.metric("Positive Stocks", f"{positive}", delta=f"{positive - 300:+d} vs threshold")

    with col3:
        st.metric("Negative Stocks", f"{negative}")

    # Gauge chart
    st.plotly_chart(
        create_sentiment_gauge(positive, total, threshold=300),
        use_container_width=True,
    )

    st.markdown("---")
    st.subheader("📊 Sentiment History")

    # Show sentiment logs from database
    from database.connection import get_session
    from database.models import SentimentLog
    from sqlalchemy import desc

    session = get_session()
    try:
        logs = session.query(SentimentLog).filter(
            SentimentLog.log_date == date.today()
        ).order_by(desc(SentimentLog.log_time)).limit(50).all()

        if logs:
            log_data = [{
                "Time": l.log_time.strftime("%H:%M:%S") if l.log_time else "",
                "Positive": l.positive_count,
                "Negative": l.negative_count,
                "Total": l.total_scanned,
                "Status": l.status,
            } for l in logs]
            st.dataframe(log_data, use_container_width=True, height=400)
        else:
            st.info("No sentiment data for today yet. Start the scanner to begin.")
    finally:
        session.close()

except Exception as e:
    st.info("Sentiment data will appear when the scanner is running.")
    st.caption(str(e))
