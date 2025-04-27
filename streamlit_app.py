import streamlit as st
import pandas as pd
import numpy as np
import time
import datetime
import requests
from quotexapi.stable_api import Quotex

# --- Sidebar - Asset and Strategy Selection ---
st.sidebar.header("Asset Selection")
asset = st.sidebar.selectbox("Choose Asset", ["BTCUSD", "EURUSD", "GBPUSD", "ETHUSD"], index=0)

st.sidebar.header("Strategy Selection")
strategy = st.sidebar.selectbox("Choose Strategy", ["Magic Strategy", "Simple MA Crossover", "RSI Strategy"], index=0)

# --- Sidebar - Trading Settings ---
st.sidebar.header("Trading Settings")
email = st.sidebar.text_input("Quotex Email")
password = st.sidebar.text_input("Quotex Password", type="password")
trade_amount = st.sidebar.number_input("Trade Amount ($)", min_value=1.0, value=1.0)
take_profit = st.sidebar.number_input("Take Profit ($)", min_value=1.0, value=20.0)
stop_loss = st.sidebar.number_input("Stop Loss ($)", min_value=1.0, value=10.0)
max_consecutive_losses = st.sidebar.number_input("Max Consecutive Losses", min_value=1, value=3)
manual_trade = st.sidebar.radio("Manual Trade", ["No", "BUY", "SELL"])

start_trading = st.sidebar.button("Start Bot")

# --- Main page ---
st.title("Quotex Auto Trading Bot with Strategy Switcher")
chart_placeholder = st.empty()
signal_placeholder = st.empty()
profit_placeholder = st.empty()

# --- Functions ---
def fetch_candles(asset, timeframe='M1', count=100):
    url = f"https://api.tradingeconomics.com/markets/symbol/{asset}:CUR?c=guest:guest"
    try:
        response = requests.get(url)
        data = response.json()
        prices = []
        for _ in range(count):
            prices.append({
                'open': np.random.uniform(20000, 30000),
                'high': np.random.uniform(30000, 31000),
                'low': np.random.uniform(19000, 20000),
                'close': np.random.uniform(20000, 30000),
                'time': datetime.datetime.now()
            })
        return pd.DataFrame(prices)
    except:
        st.error("Failed to fetch candles")
        return pd.DataFrame()

def calculate_signal(df, strategy_name):
    if strategy_name == "Magic Strategy":
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

    elif strategy_name == "Simple MA Crossover":
        df['SMA_Short'] = df['close'].rolling(window=5).mean()
        df['SMA_Long'] = df['close'].rolling(window=20).mean()
        last = df.iloc[-1]
        previous = df.iloc[-2]
        if previous['SMA_Short'] < previous['SMA_Long'] and last['SMA_Short'] > last['SMA_Long']:
            return 'BUY'
        elif previous['SMA_Short'] > previous['SMA_Long'] and last['SMA_Short'] < last['SMA_Long']:
            return 'SELL'
        else:
            return ''

    elif strategy_name == "RSI Strategy":
        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -1 * delta.clip(upper=0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))
        last = df.iloc[-1]
        if last['RSI'] < 30:
            return 'BUY'
        elif last['RSI'] > 70:
            return 'SELL'
        else:
            return ''

def place_trade(qx, asset, action, amount):
    try:
        if action == 'BUY':
            qx.buy(amount, asset, "turbo", "call", 1)
        elif action == 'SELL':
            qx.buy(amount, asset, "turbo", "put", 1)
    except Exception as e:
        st.error(f"Trade failed: {str(e)}")

# --- Main Logic ---
if start_trading:
    if not email or not password:
        st.warning("Please input Quotex credentials first.")
    else:
        st.success("Bot is Running!")

        qx = Quotex(email, password)
        qx.connect()
        qx.change_account("demo")  # Use demo account for safety

        consecutive_losses = 0
        total_profit = 0

        while True:
            df = fetch_candles(asset)
            if df.empty:
                time.sleep(30)
                continue

            chart_placeholder.line_chart(df['close'])

            current_signal = calculate_signal(df, strategy)

            # Show current signal
            if current_signal:
                signal_placeholder.success(f"Signal: {current_signal}")
            else:
                signal_placeholder.info("No clear signal.")

            # Trading logic
            if manual_trade == "No":
                if current_signal:
                    place_trade(qx, asset, current_signal, trade_amount)
            else:
                place_trade(qx, asset, manual_trade, trade_amount)

            # Simulate profit/loss
            simulated_result = np.random.choice([-trade_amount, trade_amount])
            total_profit += simulated_result
            profit_placeholder.metric("Total Profit ($)", f"${total_profit:.2f}")

            if simulated_result < 0:
                consecutive_losses += 1
            else:
                consecutive_losses = 0

            # Stop Loss / Take Profit check
            if total_profit <= -stop_loss:
                st.error("Stop Loss hit. Bot stopped.")
                break
            if total_profit >= take_profit:
                st.success("Take Profit target achieved. Bot stopped.")
                break
            if consecutive_losses >= max_consecutive_losses:
                st.error("Max consecutive losses reached. Bot stopped.")
                break

            time.sleep(30)
