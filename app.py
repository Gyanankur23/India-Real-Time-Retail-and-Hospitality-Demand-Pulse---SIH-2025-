# app.py

import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.express as px
import folium
from streamlit_folium import st_folium
from sklearn.ensemble import IsolationForest
import smtplib
from email.mime.text import MIMEText
from io import BytesIO

# -------------------- CONFIG --------------------
st.set_page_config(page_title="India Demand Pulse Dashboard", layout="wide")
SECTORS = ["Retail", "Hospitality", "Finance"]
REGIONS = ["Mumbai", "Delhi", "Chennai", "Kolkata", "Bengaluru", "Lucknow"]
DATA_FILE = "pulse_data.csv"
ALERT_EMAIL = "your-alert-email@example.com"  # Replace with actual recipient

# -------------------- DATA INIT --------------------
@st.cache_data
def load_data():
    try:
        return pd.read_csv(DATA_FILE)
    except:
        return pd.DataFrame(columns=[
            "timestamp", "region", "sector", "visitor_count", "top_items",
            "queue_time", "payment_modes", "crowd_index"
        ])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

data = load_data()

# -------------------- ALERT FUNCTION --------------------
def send_alert_email(subject, body):
    sender = "your-sender-email@example.com"
    password = "your-email-password"  # Use environment variable or secrets manager in production
    recipient = ALERT_EMAIL

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        st.success(" Alert email sent successfully!")
    except Exception as e:
        st.error(f" Failed to send alert: {e}")

# -------------------- SIDEBAR --------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", [" Submit Pulse", " Sector Dashboard", " Alerts", " Citizen View", " Export", " Recent Submissions"])

# -------------------- PAGE 1: SUBMISSION FORM --------------------
if page == " Submit Pulse":
    st.title(" Submit Daily Pulse Data")
    with st.form("pulse_form"):
        region = st.selectbox("Region", REGIONS)
        sector = st.selectbox("Sector", SECTORS)
        visitor_count = st.number_input("Visitor Count", min_value=0)
        top_items = st.text_input("Top-Selling Items / Services")
        queue_time = st.number_input("Average Queue Time (minutes)", min_value=0)
        payment_modes = st.multiselect("Payment Breakdown", ["Cash", "Card", "UPI", "Wallet"])
        crowd_index = st.slider("Crowd Index (0 = Empty, 10 = Overwhelmed)", 0, 10)
        submitted = st.form_submit_button("Submit")

    if submitted:
        new_entry = pd.DataFrame([{
            "timestamp": datetime.datetime.now(),
            "region": region,
            "sector": sector,
            "visitor_count": visitor_count,
            "top_items": top_items,
            "queue_time": queue_time,
            "payment_modes": ",".join(payment_modes),
            "crowd_index": crowd_index
        }])
        updated_data = pd.concat([data, new_entry], ignore_index=True)
        save_data(updated_data)
        st.success("✅ Data submitted successfully!")

# -------------------- PAGE 2: DASHBOARD --------------------
elif page == " Sector Dashboard":
    st.title(" Sector-Wise Demand Dashboard")
    sector = st.selectbox("Select Sector", SECTORS)
    filtered = data[data["sector"] == sector]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Average Crowd Index", round(filtered["crowd_index"].mean(), 2))
        st.metric("Average Queue Time", round(filtered["queue_time"].mean(), 2))
    with col2:
        fig = px.histogram(filtered, x="region", y="visitor_count", color="region", title="Visitor Count by Region")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader(" Crowd Heatmap")
    m = folium.Map(location=[20.5937, 78.9629], zoom_start=4)
    for _, row in filtered.iterrows():
        lat = np.random.uniform(8, 37)
        lon = np.random.uniform(68, 97)
        folium.CircleMarker(
            location=[lat, lon],
            radius=row["crowd_index"],
            popup=f"{row['region']} ({row['crowd_index']})",
            color="red",
            fill=True
        ).add_to(m)
    st_folium(m, width=700)

# -------------------- PAGE 3: ALERTS --------------------
elif page == " Alerts":
    st.title(" Real-Time Surge & Anomaly Alerts")
    if len(data) < 10:
        st.warning("Not enough data for anomaly detection.")
    else:
        model = IsolationForest(contamination=0.1)
        features = data[["visitor_count", "queue_time", "crowd_index"]]
        data["anomaly"] = model.fit_predict(features)
        alerts = data[data["anomaly"] == -1]

        for _, row in alerts.iterrows():
            alert_msg = f"⚠️ Alert: Unusual activity in {row['region']} ({row['sector']}) — Crowd Index {row['crowd_index']}, Queue Time {row['queue_time']} mins"
            st.error(alert_msg)
            send_alert_email(
                subject=f"Alert: {row['sector']} anomaly in {row['region']}",
                body=alert_msg
            )

# -------------------- PAGE 4: CITIZEN VIEW --------------------
elif page == " Citizen View":
    st.title(" Citizen Pulse — Check Crowd Levels")
    region = st.selectbox("Your Region", REGIONS)
    sector = st.selectbox("Service Type", SECTORS)
    latest = data[(data["region"] == region) & (data["sector"] == sector)].sort_values("timestamp", ascending=False).head(1)

    if latest.empty:
        st.info("No recent data available for your selection.")
    else:
        row = latest.iloc[0]
        st.metric("Crowd Index", row["crowd_index"])
        st.metric("Queue Time", f"{row['queue_time']} mins")
        st.write(f"Top Requests: {row['top_items']}")
        st.write(f"Payment Modes: {row['payment_modes']}")

# -------------------- PAGE 5: EXPORT --------------------
elif page == " Export":
    st.title(" Export Data for Policy Teams")
    export_format = st.radio("Choose Format", ["CSV", "Excel"])
    if export_format == "CSV":
        st.download_button("Download CSV", data.to_csv(index=False), file_name="pulse_data.csv")
    else:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            data.to_excel(writer, index=False, sheet_name='PulseData')
        st.download_button("Download Excel", output.getvalue(), file_name="pulse_data.xlsx")

# -------------------- PAGE 6: RECENT SUBMISSIONS --------------------
elif page == "Recent Submissions":
    st.title("Recent Pulse Submissions")
    st.dataframe(data.sort_values("timestamp", ascending=False).head(20))

# -------------------- FOOTER --------------------
st.markdown("---")
st.caption("Built for India’s Smart Governance • Privacy-Safe • Scalable • Open Source")

region = st.selectbox("Your Region", REGIONS)
sector = st.selectbox("Service Type", SECTORS)
latest = data[(data["region"] == region) & (data["sector"] == sector)].sort_values("timestamp", ascending=False).head(1)
    if latest.empty:
        st.info("No recent data available for your selection.")
    else:
        row = latest.iloc[0]
        st.metric("Crowd Index", row["crowd_index"])
        st.metric("Queue Time", f"{row['queue_time']} mins")
        st.write(f"Top Requests: {row['top_items']}")
        st.write(f"Payment Modes: {row['payment_modes']}")

# -------------------- PAGE 5: EXPORT --------------------
elif page == "Export":
    st.title(" Export Data for Policy Teams")
    export_format = st.radio("Choose Format", ["CSV", "Excel"])
    if export_format == "CSV":
        st.download_button("Download CSV", data.to_csv(index=False), file_name="pulse_data.csv")
    else:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            data.to_excel(writer, index=False, sheet_name='PulseData')
        st.download_button("Download Excel", output.getvalue(), file_name="pulse_data.xlsx")

# -------------------- FOOTER --------------------
st.markdown("---")
st.caption("Built for India’s Smart Governance • Privacy-Safe • Scalable • Open Source")
