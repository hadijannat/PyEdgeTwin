#!/usr/bin/env python3
"""PyEdgeTwin Dashboard - Motor Filtering Demo.

A Streamlit dashboard that visualizes:
- Raw sensor values vs Kalman-filtered estimates
- Anomaly detection events
- Real-time streaming data from InfluxDB
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from influxdb_client import InfluxDBClient

# Configuration from environment
INFLUXDB_URL = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.environ.get("INFLUXDB_TOKEN", "dev-token-pyedgetwin-12345")
INFLUXDB_ORG = os.environ.get("INFLUXDB_ORG", "pyedgetwin")
INFLUXDB_BUCKET = os.environ.get("INFLUXDB_BUCKET", "twins")

# Page configuration
st.set_page_config(
    page_title="PyEdgeTwin Dashboard",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Title
st.title("🔧 PyEdgeTwin - Motor Filtering Demo")
st.markdown("""
This dashboard visualizes the Kalman filter digital twin processing motor temperature data.
- **Raw Value**: Noisy sensor measurement
- **Twin Estimate**: Kalman-filtered estimate
- **Anomalies**: Detected anomalous readings
""")


@st.cache_resource
def get_influx_client() -> InfluxDBClient:
    """Get or create InfluxDB client."""
    return InfluxDBClient(
        url=INFLUXDB_URL,
        token=INFLUXDB_TOKEN,
        org=INFLUXDB_ORG,
    )


def query_data(time_range: str) -> pd.DataFrame:
    """Query data from InfluxDB."""
    client = get_influx_client()
    query_api = client.query_api()

    query = f'''
    from(bucket: "{INFLUXDB_BUCKET}")
      |> range(start: {time_range})
      |> filter(fn: (r) => r._measurement == "motor_twin")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"])
    '''

    try:
        result = query_api.query_data_frame(query)
        if isinstance(result, list):
            result = pd.concat(result) if result else pd.DataFrame()
        return result
    except Exception as e:
        st.error(f"Error querying InfluxDB: {e}")
        return pd.DataFrame()


# Sidebar controls
st.sidebar.header("⚙️ Controls")

time_range = st.sidebar.selectbox(
    "Time Range",
    options=["-1m", "-5m", "-15m", "-30m", "-1h", "-6h"],
    index=1,  # Default to -5m
    help="Select the time range to display",
)

auto_refresh = st.sidebar.checkbox(
    "Auto Refresh (5s)",
    value=True,
    help="Automatically refresh data every 5 seconds",
)

# Query data
df = query_data(time_range)

if df.empty:
    st.info("⏳ No data available yet. Start the twin runtime to see data flowing.")
    st.markdown("""
    **Quick Start:**
    ```bash
    cd examples/motor_filtering
    docker compose up -d
    ```
    """)
else:
    # Ensure _time is datetime
    if "_time" in df.columns:
        df["_time"] = pd.to_datetime(df["_time"])
        df = df.set_index("_time")

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Data Points",
            len(df),
        )

    with col2:
        if "anomaly_flag" in df.columns:
            anomaly_count = df["anomaly_flag"].sum() if df["anomaly_flag"].dtype == bool else (df["anomaly_flag"] == True).sum()
            st.metric("Anomalies Detected", int(anomaly_count))
        else:
            st.metric("Anomalies Detected", "N/A")

    with col3:
        if "twin_estimate" in df.columns:
            current_temp = df["twin_estimate"].iloc[-1]
            st.metric("Current Estimate", f"{current_temp:.1f}°C")
        else:
            st.metric("Current Estimate", "N/A")

    with col4:
        if "residual" in df.columns:
            avg_residual = df["residual"].abs().mean()
            st.metric("Avg |Residual|", f"{avg_residual:.2f}°C")
        else:
            st.metric("Avg |Residual|", "N/A")

    # Charts
    st.subheader("📈 Temperature: Raw vs Filtered")

    if "raw_value" in df.columns and "twin_estimate" in df.columns:
        chart_data = df[["raw_value", "twin_estimate"]].copy()
        chart_data.columns = ["Raw Sensor", "Kalman Estimate"]
        st.line_chart(chart_data, height=400)
    else:
        st.warning("Missing raw_value or twin_estimate columns")

    # Two-column layout for additional charts
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📊 Residual (Raw - Estimate)")
        if "residual" in df.columns:
            st.line_chart(df["residual"], height=250)
        else:
            st.info("Residual data not available")

    with col_right:
        st.subheader("🚨 Anomaly Events")
        if "anomaly_flag" in df.columns:
            # Convert to numeric if needed
            anomaly_data = df["anomaly_flag"].astype(float)
            st.line_chart(anomaly_data, height=250)
        else:
            st.info("Anomaly data not available")

    # Kalman gain visualization
    if "kalman_gain" in df.columns:
        st.subheader("🎯 Kalman Gain Over Time")
        st.line_chart(df["kalman_gain"], height=200)
        st.caption("Kalman gain adapts based on prediction uncertainty. Higher = trusting measurements more.")

    # Recent data table
    st.subheader("📋 Recent Data")
    display_cols = [
        col for col in ["raw_value", "twin_estimate", "anomaly_flag", "residual", "kalman_gain"]
        if col in df.columns
    ]
    if display_cols:
        st.dataframe(
            df[display_cols].tail(20).round(3),
            use_container_width=True,
        )

# Connection status in sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("📡 Connection Status")

try:
    client = get_influx_client()
    health = client.health()
    if health.status == "pass":
        st.sidebar.success(f"✅ InfluxDB: Connected")
    else:
        st.sidebar.warning(f"⚠️ InfluxDB: {health.status}")
except Exception as e:
    st.sidebar.error(f"❌ InfluxDB: {str(e)[:50]}")

st.sidebar.markdown(f"**URL:** `{INFLUXDB_URL}`")
st.sidebar.markdown(f"**Bucket:** `{INFLUXDB_BUCKET}`")

# Auto-refresh
if auto_refresh:
    import time
    time.sleep(5)
    st.rerun()

# Footer
st.sidebar.markdown("---")
st.sidebar.markdown("""
**PyEdgeTwin**
Python runtime for hybrid model deployment on edge devices.

[GitHub](https://github.com/aeroshariati/PyEdgeTwin)
""")
