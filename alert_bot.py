"""
Bot de ALERTAS por Telegram (no ejecuta ordenes, solo te avisa).

Estrategia: cruce de medias moviles (SMA rapida/lenta) + RSI, con niveles
de stop-loss / take-profit calculados sobre un precio de entrada hipotetico
que se actualiza cuando te avisa "COMPRA".

Te envia un mensaje de Telegram cuando detecta:
  - Señal de COMPRA (cruce alcista + RSI no sobrecomprado)
  - Señal de VENTA (cruce bajista, stop-loss, take-profit, o RSI sobrecomprado)

Configuracion (gratis, 5 minutos):
  1. En Telegram, habla con @BotFather y envia /newbot. Sigue las
     instrucciones (nombre, username). Te dara un TOKEN.
  2. Busca tu bot recien creado en Telegram y envia cualquier mensaje
     (ej. "hola") para iniciar el chat.
  3. Visita en el navegador:
     https://api.telegram.org/bot<TU_TOKEN>/getUpdates
     y busca el campo "chat":{"id": ...} — ese numero es tu CHAT_ID.

Variables de entorno necesarias:
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID
"""
import os
import time
import json
import logging
from datetime import datetime, timezone

import ccxt
import pandas as pd
import numpy as np
import requests

# ---------- Parametros (configurables via variables de entorno) ----------
SYMBOL = os.getenv("SYMBOL", "BTC/USDT")
TIMEFRAME = os.getenv("TIMEFRAME", "1h")
FAST_MA = int(os.getenv("FAST_MA", 20))
SLOW_MA = int(os.getenv("SLOW_MA", 50))
RSI_PERIOD = int(os.getenv("RSI_PERIOD", 14))
RSI_OVERBOUGHT = float(os.getenv("RSI_OVERBOUGHT", 70))
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", 0.03))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", 0.06))
CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", 300))  # 5 min
STATE_FILE = os.getenv("STATE_FILE", "alert_state.json")

# ---------- Credenciales de Telegram ----------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("alert_bot")

exchange = ccxt.kraken()


def send_telegram(message: str):
    log.info(f"ALERTA: {message}")
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("Telegram no configurado (faltan credenciales) - solo se registra en logs.")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        resp = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
        if resp.status_code != 200:
            log.error(f"Error enviando Telegram: {resp.status_code} {resp.text}")
    except Exception as e:
        log.error(f"Error enviando Telegram: {e}")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"in_position": False, "entry_price": None}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)


def fetch_recent_candles(limit=200):
    candles = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=limit)
    df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def compute_indicators(df):
    df["sma_fast"] = df["close"].rolling(FAST_MA).mean()
    df["sma_slow"] = df["close"].rolling(SLOW_MA).mean()

    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(RSI_PERIOD).mean()
    avg_loss = loss.rolling(RSI_PERIOD).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))
    return df


def check_signals(df, state):
    last = df.iloc[-1]
    prev = df.iloc[-2]
    price = last["close"]

    bullish_cross = prev["sma_fast"] <= prev["sma_slow"] and last["sma_fast"] > last["sma_slow"]
    bearish_cross = prev["sma_fast"] >= prev["sma_slow"] and last["sma_fast"] < last["sma_slow"]

    if not state["in_position"]:
        if bullish_cross and last["rsi"] < RSI_OVERBOUGHT:
            state["in_position"] = True
            state["entry_price"] = price
            send_telegram(
                f"🟢 SEÑAL DE COMPRA — {SYMBOL}\n"
                f"Precio: ${price:,.2f}\n"
                f"RSI: {last['rsi']:.1f}\n"
                f"Stop-loss sugerido: ${price * (1 - STOP_LOSS_PCT):,.2f}\n"
                f"Take-profit sugerido: ${price * (1 + TAKE_PROFIT_PCT):,.2f}"
            )
    else:
        entry_price = state["entry_price"]
        change_pct = (price - entry_price) / entry_price
        hit_stop = change_pct <= -STOP_LOSS_PCT
        hit_target = change_pct >= TAKE_PROFIT_PCT
        exit_signal = bearish_cross or hit_stop or hit_target or last["rsi"] > RSI_OVERBOUGHT

        if exit_signal:
            if hit_stop:
                reason = "Stop-loss alcanzado"
            elif hit_target:
                reason = "Take-profit alcanzado"
            elif last["rsi"] > RSI_OVERBOUGHT:
                reason = "RSI sobrecomprado"
            else:
                reason = "Cruce bajista de medias"

            send_telegram(
                f"🔴 SEÑAL DE VENTA — {SYMBOL}\n"
                f"Motivo: {reason}\n"
                f"Precio: ${price:,.2f}\n"
                f"Retorno desde entrada: {change_pct*100:.2f}%"
            )
            state["in_position"] = False
            state["entry_price"] = None

    log.info(f"Precio actual: ${price:,.2f} | RSI: {last['rsi']:.1f} | En posición: {state['in_position']}")
    return state


def main():
    state = load_state()
    df = fetch_recent_candles(limit=max(SLOW_MA, RSI_PERIOD) + 50)
    df = compute_indicators(df)
    state = check_signals(df, state)
    save_state(state)


if __name__ == "__main__":
    main()
