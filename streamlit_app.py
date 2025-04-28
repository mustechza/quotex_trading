import streamlit as st
import pandas as pd
import requests
import time

# ========== Settings ==========
ASSETS = ['ETHUSDT', 'SOLUSDT', 'ADAUSDT', 'BNBUSDT', 'XRPUSDT', 'LTCUSDT']
CANDLE_INTERVAL = '1m'  # 1 minute
CANDLE_LIMIT = 500
TRADE_AMOUNT = 1  # $ per trade
START_BALANCE = 100  # starting balance

# ========== Helper Functions ==========

def get_binance_candles(symbol, interval='1m', limit=500):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['close'] = df['close'].astype(float)
    df.set_index('timestamp', inplace=True)
    return df[['close']]

def compute_indicators(df):
    df['EMA5'] = df['close'].ewm(span=5, adjust=False).mean()
    df['EMA20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['RSI'] = compute_rsi(df['close'], 14)
    return df

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def magic_secret_strategy(df):
    if len(df) >= 20:
        if not pd.isna(df['EMA5'].iloc[-1]) and not pd.isna(df['EMA20'].iloc[-1]) and not pd.isna(df['RSI'].iloc[-1]):
            if df['EMA5'].iloc[-1] > df['EMA20'].iloc[-1] and df['RSI'].iloc[-1] > 50:
                return 'CALL'
            elif df['EMA5'].iloc[-1] < df['EMA20'].iloc[-1] and df['RSI'].iloc[-1] < 50:
                return 'PUT'
    return None

def ema_cross_only_strategy(df):
    if len(df) >= 20:
        if not pd.isna(df['EMA5'].iloc[-1]) and not pd.isna(df['EMA20'].iloc[-1]):
            if df['EMA5'].iloc[-1] > df['EMA20'].iloc[-1]:
                return 'CALL'
            elif df['EMA5'].iloc[-1] < df['EMA20'].iloc[-1]:
                return 'PUT'
    return None

def rsi_divergence_strategy(df):
    if len(df) >= 14:
        if not pd.isna(df['RSI'].iloc[-1]):
            if df['RSI'].iloc[-1] < 30:
                return 'CALL'
            elif df['RSI'].iloc[-1] > 70:
                return 'PUT'
    return None

def generate_signal(df, strategy_name):
    if strategy_name == "Magic Secret":
        return magic_secret_strategy(df)
    elif strategy_name == "EMA Cross":
        return ema_cross_only_strategy(df)
    elif strategy_name == "RSI Divergence":
        return rsi_divergence_strategy(df)
    return None

# ========== Streamlit App ==========

st.set_page_config(page_title="Quotex Signal Sender", layout="wide")
st.title("Quotex Manual Signal Sender")

col1, col2 = st.columns(2)

with col1:
    selected_asset = st.selectbox("Select Asset", ASSETS)

with col2:
    selected_strategy = st.selectbox("Select Strategy", ["Magic Secret", "EMA Cross", "RSI Divergence"])

take_profit = st.number_input("Take Profit ($)", min_value=1, value=10)
stop_loss = st.number_input("Stop Loss ($)", min_value=1, value=10)

start = st.button("Start")

if 'running' not in st.session_state:
    st.session_state.running = False
if start:
    st.session_state.running = True

balance = st.session_state.get('balance', START_BALANCE)
trade_history = st.session_state.get('trade_history', [])

if st.session_state.running:
    placeholder_chart = st.empty()
    placeholder_alert = st.empty()
    placeholder_balance = st.empty()

    while st.session_state.running:
        df = get_binance_candles(selected_asset, interval=CANDLE_INTERVAL, limit=CANDLE_LIMIT)
        df = compute_indicators(df)
        
        signal = generate_signal(df, selected_strategy)

        placeholder_chart.line_chart(df['close'])

        if signal:
            with placeholder_alert.container():
                st.success(f"Signal: {signal} for {selected_asset} with {selected_strategy} strategy!")

            # Simulate trade
            result = 'WIN' if signal == ('CALL' if df['close'].iloc[-1] > df['close'].iloc[-2] else 'PUT') else 'LOSS'

            if result == 'WIN':
                balance += TRADE_AMOUNT
            else:
                balance -= TRADE_AMOUNT

            trade_history.append({
                'Asset': selected_asset,
                'Strategy': selected_strategy,
                'Signal': signal,
                'Result': result,
                'Balance': balance,
                'Time': pd.Timestamp.now()
            })

            st.session_state.balance = balance
            st.session_state.trade_history = trade_history

            if balance - START_BALANCE >= take_profit:
                st.success(f"Take profit reached: ${balance}!")
                st.session_state.running = False
                break
            if START_BALANCE - balance >= stop_loss:
                st.error(f"Stop loss hit: ${balance}!")
                st.session_state.running = False
                break

        placeholder_balance.metric("Balance", f"${balance:.2f}")

        time.sleep(30)  # Update every 30 seconds

if st.session_state.get('trade_history'):
    st.subheader("Trade History")
    st.dataframe(pd.DataFrame(st.session_state.trade_history))
