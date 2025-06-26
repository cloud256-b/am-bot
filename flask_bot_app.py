from flask import Flask, render_template, jsonify, request
from threading import Thread
import time
import pandas as pd
import numpy as np
from datetime import datetime

app = Flask(__name__)

# Bot configuration
SYMBOL = 'BTC/USDT'
TIMEFRAME = '15m'
INITIAL_BALANCE = 10
RISK_PER_TRADE = 0.02
LEVERAGE = 1
running = False
log = []
balance = INITIAL_BALANCE

# Mock exchange data
def mock_fetch_ohlcv(symbol, timeframe, limit=100):
    timestamps = pd.date_range(end=datetime.now(), periods=limit, freq='15min')
    data = {
        'timestamp': timestamps,
        'open': np.random.uniform(29000, 31000, size=limit),
        'high': np.random.uniform(31000, 32000, size=limit),
        'low': np.random.uniform(28000, 30000, size=limit),
        'close': np.random.uniform(29000, 31000, size=limit),
        'volume': np.random.uniform(10, 100, size=limit)
    }
    return pd.DataFrame(data)

def get_ohlcv():
    return mock_fetch_ohlcv(SYMBOL, TIMEFRAME)

def identify_valid_highs_lows(df):
    df['high_peak'] = df['high'][(df['high'] > df['high'].shift(1)) & (df['high'] > df['high'].shift(-1))]
    df['low_trough'] = df['low'][(df['low'] < df['low'].shift(1)) & (df['low'] < df['low'].shift(-1))]
    return df

def detect_zones(df, sensitivity=2):
    zones = []
    for i in range(sensitivity, len(df) - sensitivity):
        if df['high'][i] == max(df['high'][i-sensitivity:i+sensitivity+1]):
            zones.append(('resistance', df['high'][i]))
        elif df['low'][i] == min(df['low'][i-sensitivity:i+sensitivity+1]):
            zones.append(('support', df['low'][i]))
    return zones

def check_bullish_setup(df):
    recent = df.tail(10)
    lows = recent['low_trough'].dropna()
    highs = recent['high_peak'].dropna()
    if len(lows) >= 2 and len(highs) >= 2:
        low1, low2 = lows.iloc[-2], lows.iloc[-1]
        high1, high2 = highs.iloc[-2], highs.iloc[-1]
        if low2 > low1 and high2 > high1:
            entry = df['close'].iloc[-1]
            sl = low2
            tp = entry + (entry - sl) * 2
            return entry, sl, tp
    return None

def check_bearish_setup(df):
    recent = df.tail(10)
    lows = recent['low_trough'].dropna()
    highs = recent['high_peak'].dropna()
    if len(lows) >= 2 and len(highs) >= 2:
        low1, low2 = lows.iloc[-2], lows.iloc[-1]
        high1, high2 = highs.iloc[-2], highs.iloc[-1]
        if low2 < low1 and high2 < high1:
            entry = df['close'].iloc[-1]
            sl = high2
            tp = entry - (sl - entry) * 2
            return entry, sl, tp
    return None

def calculate_position_size(entry, sl, balance):
    risk_amount = balance * RISK_PER_TRADE
    price_diff = abs(entry - sl)
    if price_diff == 0:
        return 0
    position_size = risk_amount / price_diff
    return min(position_size, balance / entry)

def execute_trade(side, entry, sl, tp, size):
    msg = f"[MOCK TRADE] {side.upper()} | Entry: {entry}, SL: {sl}, TP: {tp}, Size: {size}"
    log.append(msg)
    print(msg)

def bot_loop():
    global running, balance
    while running:
        try:
            if balance < 5:
                log.append("Balance too low, stopping bot")
                break

            df = get_ohlcv()
            df = identify_valid_highs_lows(df)
            detect_zones(df)

            bullish_trade = check_bullish_setup(df)
            bearish_trade = check_bearish_setup(df)

            if bullish_trade:
                entry, sl, tp = bullish_trade
                size = calculate_position_size(entry, sl, balance)
                execute_trade('long', entry, sl, tp, size)

            if bearish_trade:
                entry, sl, tp = bearish_trade
                size = calculate_position_size(entry, sl, balance)
                execute_trade('short', entry, sl, tp, size)

            time.sleep(60)
        except Exception as e:
            log.append(f"Error: {e}")
            time.sleep(60)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start')
def start():
    global running
    if not running:
        running = True
        Thread(target=bot_loop).start()
    return jsonify({'status': 'bot started'})

@app.route('/stop')
def stop():
    global running
    running = False
    return jsonify({'status': 'bot stopped'})

@app.route('/logs')
def get_logs():
    return jsonify({'logs': log[-50:]})

if __name__ == '__main__':
    app.run(debug=True)
