import streamlit as st
import time as t
import pandas as pd
from quotexapi.stable_api import Quotex
import datetime
import requests

# --- Login ---
st.title("Quotex Magic Strategy Bot")
st.sidebar.header("Login to Quotex")

email = st.sidebar.text_input("Email")
password = st.sidebar.text_input("Password", type="password")
login_button = st.sidebar.button("Login and Start Bot")

if login_button:
    try:
        q = Quotex(email, password)
        if q.check_connect():
            st.sidebar.success("Connected to Quotex!")
            logged_in = True
        else:
            st.sidebar.error("Login failed.")
            logged_in = False
    except Exception as e:
        st.sidebar.error(f"Login error: {e}")
        logged_in = False
else:
    logged_in = False

if logged_in:

    # --- Settings ---
    st.sidebar.header("Trading Settings")
    investment = st.sidebar.number_input("Investment per trade ($)", min_value=1, max_value=1000, value=1)
    direction_time = st.sidebar.selectbox("Trade Duration", ["1", "2", "3"], index=0)

    st.sidebar.header("Risk Management")
    max_loss = st.sidebar.number_input("Max Loss ($)", min_value=1, max_value=500, value=20)
    max_consecutive_losses = st.sidebar.number_input("Max Consecutive Losses", min_value=1, max_value=10, value=3)
    take_profit = st.sidebar.number_input("Take Profit ($)", min_value=5, max_value=1000, value=50)

    st.sidebar.header("Manual Trading")
    manual_buy = st.sidebar.button("Manual BUY")
    manual_sell = st.sidebar.button("Manual SELL")

    # Initialize variables
    asset = "BTCUSD"
    total_profit = 0
    consecutive_losses = 0
    auto_trading_enabled = True
    last_signal = ''
    current_signal = ''

    # --- Functions ---

    def get_candles():
        now = int(t.time())
        candles = q.get_candles(asset=asset, interval=60, limit=100)
        df = pd.DataFrame(candles)
        df['close'] = df['close'].astype(float)
        return df

    def calculate_magic_signal(df):
        df['heiken_ashi'] = (df['open'] + df['close'] + df['high'] + df['low']) / 4
        df['MA'] = df['heiken_ashi'].rolling(window=10).mean()
        df['ROC'] = df['heiken_ashi'].pct_change(periods=5)
        last = df.iloc[-1]

        if last['heiken_ashi'] > last['MA'] and last['ROC'] > 0:
            return 'BUY'
        elif last['heiken_ashi'] < last['MA'] and last['ROC'] < 0:
            return 'SELL'
        else:
            return ''

    # --- Main Loop ---

    st.success("Bot is Running!")

    while True:
        df = get_candles()
        current_signal = calculate_magic_signal(df)

        if current_signal and current_signal != last_signal and auto_trading_enabled:
            st.subheader(f"NEW SIGNAL: {current_signal}")

            if current_signal == "BUY":
                try:
                    q.buy(amount=investment, asset=asset, direction="
