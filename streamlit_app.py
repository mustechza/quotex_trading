import streamlit as st
from quotexapi.stable_api import Quotex
from dotenv import load_dotenv
import os
import time

# Load .env file
load_dotenv()

st.set_page_config(page_title="Quotex Trading App", layout="centered")
st.title("📈 Quotex Trader")

# Secure session id input
ssid = st.text_input("Enter your Quotex ssid", value=os.getenv("QX_SSID", ""), type="password")
asset = st.selectbox("Choose Asset", ["EURUSD", "GBPUSD", "BTCUSD", "AUDCAD", "USDJPY"])
amount = st.number_input("Amount ($)", min_value=1.0, value=1.0)
duration = st.slider("Duration (seconds)", min_value=30, max_value=300, value=60, step=30)
direction = st.radio("Direction", ["call", "put"])
balance_type = st.radio("Account Type", ["PRACTICE", "REAL"])

if st.button("📤 Place Trade"):
    if not ssid:
        st.error("Please provide a valid ssid.")
    else:
        qx = Quotex(set_ssid=ssid)
        st.write("🔌 Connecting to Quotex...")
        if qx.connect():
            qx.change_balance(balance_type)
            success = qx.buy(amount=amount, asset=asset, direction=direction, duration=duration)
            if success:
                st.success(f"Trade placed successfully on {asset.upper()} ({direction.upper()})")
                with st.spinner("⏳ Waiting for result..."):
                    time.sleep(duration + 5)
                    result = qx.check_win()
                    if result["win"] == "win":
                        st.success(f"✅ Trade WON: Profit = ${result['profit']}")
                    elif result["win"] == "loose":
                        st.error(f"❌ Trade LOST: Loss = ${result['profit']}")
                    else:
                        st.warning("⚠️ Trade result: ", result["win"])
            else:
                st.error("Trade failed to execute.")
        else:
            st.error("❌ Failed to connect to Quotex.")
