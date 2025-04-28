import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import time

# ========== SETTINGS ==========
ASSETS = ['ETH/USDT', 'SOL/USDT', 'ADA/USDT', 'BNB/USDT', 'XRP/USDT', 'LTC/USDT']
STRATEGIES = ['Magic Secret', 'RSI Divergence', 'EMA Cross Only']
UPDATE_INTERVAL = 60  # seconds
CANDLE_LIMIT = 500  # for backtest mode

# ========== FUNCTIONS ==========

def fetch_binance_candles(symbol, interval='1m', limit=500):
    symbol = symbol.replace('/', '')
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    r = requests.get(url)
    data = r.json()
    candles = pd.DataFrame(data, columns=['time','open','high','low','close','volume','close_time','qav','n_trades','tbbav','tbqav','ignore'])
    candles['time'] = pd.to_datetime(candles['time'], unit='ms')
    candles['open'] = candles['open'].astype(float)
    candles['high'] = candles['high'].astype(float)
    candles['low'] = candles['low'].astype(float)
    candles['close'] = candles['close'].astype(float)
    candles['volume'] = candles['volume'].astype(float)
    return candles[['time','open','high','low','close','volume']]

def magic_secret_strategy(df):
    df['EMA5'] = df['close'].ewm(span=5).mean()
    df['EMA20'] = df['close'].ewm(span=20).mean()
    df['RSI'] = compute_rsi(df['close'], 14)
    signal = None
    if df['EMA5'].iloc[-1] > df['EMA20'].iloc[-1] and df['RSI'].iloc[-1] > 50:
        signal = 'CALL'
    elif df['EMA5'].iloc[-1] < df['EMA20'].iloc[-1] and df['RSI'].iloc[-1] < 50:
        signal = 'PUT'
    return signal

def ema_cross_only_strategy(df):
    df['EMA5'] = df['close'].ewm(span=5).mean()
    df['EMA20'] = df['close'].ewm(span=20).mean()
    signal = None
    if df['EMA5'].iloc[-1] > df['EMA20'].iloc[-1]:
        signal = 'CALL'
    elif df['EMA5'].iloc[-1] < df['EMA20'].iloc[-1]:
        signal = 'PUT'
    return signal

def rsi_divergence_strategy(df):
    df['RSI'] = compute_rsi(df['close'], 14)
    signal = None
    if df['RSI'].iloc[-1] < 30:
        signal = 'CALL'
    elif df['RSI'].iloc[-1] > 70:
        signal = 'PUT'
    return signal

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=period).mean()
    avg_loss = pd.Series(loss).rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def generate_signal(df, strategy):
    if strategy == 'Magic Secret':
        return magic_secret_strategy(df)
    elif strategy == 'EMA Cross Only':
        return ema_cross_only_strategy(df)
    elif strategy == 'RSI Divergence':
        return rsi_divergence_strategy(df)
    else:
        return None

# ========== STREAMLIT UI ==========

st.set_page_config(page_title="Crypto Signal App", layout="wide")
st.title("Manual Trading Signal Generator")
menu = st.sidebar.selectbox("Select Mode", ["Live Trading", "Backtest", "Settings"])
st.sidebar.markdown("---")

selected_asset = st.sidebar.selectbox("Select Asset", ASSETS)
selected_strategy = st.sidebar.selectbox("Select Strategy", STRATEGIES)

if 'trade_log' not in st.session_state:
    st.session_state['trade_log'] = []

# ========== LIVE TRADING ==========
if menu == "Live Trading":
    placeholder = st.empty()

    while True:
        with placeholder.container():
            df = fetch_binance_candles(selected_asset, '1m', 100)
            signal = generate_signal(df, selected_strategy)

            st.subheader(f"Asset: {selected_asset}")
            st.subheader(f"Strategy: {selected_strategy}")
            st.metric(label="Signal", value=signal if signal else "No Signal", delta_color="normal")
            st.line_chart(df.set_index('time')['close'])

            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if signal:
                st.session_state.trade_log.append({"time": now, "asset": selected_asset, "strategy": selected_strategy, "signal": signal})

            time.sleep(UPDATE_INTERVAL)

# ========== BACKTEST ==========
elif menu == "Backtest":
    st.subheader("Backtest Mode")
    df = fetch_binance_candles(selected_asset, '1m', CANDLE_LIMIT)
    df['Signal'] = df.apply(lambda row: generate_signal(df.iloc[:row.name+1], selected_strategy), axis=1)
    st.dataframe(df[['time','close','Signal']])
    st.line_chart(df.set_index('time')['close'])

# ========== SETTINGS ==========
elif menu == "Settings":
    st.subheader("Settings & Trade History")
    if st.session_state.trade_log:
        trades = pd.DataFrame(st.session_state.trade_log)
        st.dataframe(trades)
        st.download_button("Download Trade History CSV", data=trades.to_csv(index=False), file_name="trade_history.csv", mime='text/csv')
        calls = trades[trades['signal']=='CALL']
        puts = trades[trades['signal']=='PUT']
        total = len(trades)
        st.write(f"Total Signals: {total}")
        st.write(f"CALLs: {len(calls)}")
        st.write(f"PUTs: {len(puts)}")
    else:
        st.info("No trades logged yet.")
