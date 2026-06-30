"""
Backtest de estrategia momentum (cruce de medias moviles + RSI + stop-loss)
para BTC/USDT usando datos historicos publicos de Binance via ccxt.

Uso:
    python backtest.py
"""
import ccxt
import pandas as pd
import numpy as np

# ---------- Parametros de la estrategia ----------
SYMBOL = "BTC/USDT"
TIMEFRAME = "1h"
LOOKBACK_CANDLES = 24 * 365  # ~1 año de velas de 1h
FAST_MA = 20
SLOW_MA = 50
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
STOP_LOSS_PCT = 0.03      # 3%
TAKE_PROFIT_PCT = 0.06    # 6%
INITIAL_CAPITAL = 1000.0
FEE_PCT = 0.001            # 0.1% por operacion (taker fee tipico)


def fetch_ohlcv(symbol, timeframe, limit):
    exchange = ccxt.binance()
    all_candles = []
    since = exchange.milliseconds() - limit * exchange.parse_timeframe(timeframe) * 1000
    while len(all_candles) < limit:
        candles = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
        if not candles:
            break
        all_candles += candles
        since = candles[-1][0] + 1
        if len(candles) < 1000:
            break
    df = pd.DataFrame(all_candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.drop_duplicates(subset="timestamp").reset_index(drop=True)
    return df.tail(limit).reset_index(drop=True)


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


def run_backtest(df):
    capital = INITIAL_CAPITAL
    position = None  # dict con entry_price, size
    equity_curve = []
    trades = []

    for i in range(SLOW_MA + RSI_PERIOD, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]
        price = row["close"]

        # Señal de entrada: cruce alcista de medias + RSI no sobrecomprado
        bullish_cross = prev["sma_fast"] <= prev["sma_slow"] and row["sma_fast"] > row["sma_slow"]
        bearish_cross = prev["sma_fast"] >= prev["sma_slow"] and row["sma_fast"] < row["sma_slow"]

        if position is None:
            if bullish_cross and row["rsi"] < RSI_OVERBOUGHT:
                size = capital / price
                entry_fee = capital * FEE_PCT
                capital -= entry_fee
                position = {"entry_price": price, "size": size, "entry_idx": i}
        else:
            entry_price = position["entry_price"]
            change_pct = (price - entry_price) / entry_price
            exit_signal = (
                bearish_cross
                or change_pct <= -STOP_LOSS_PCT
                or change_pct >= TAKE_PROFIT_PCT
                or row["rsi"] > RSI_OVERBOUGHT
            )
            if exit_signal:
                proceeds = position["size"] * price
                exit_fee = proceeds * FEE_PCT
                capital = proceeds - exit_fee
                trades.append({
                    "entry_price": entry_price,
                    "exit_price": price,
                    "pct_return": change_pct,
                    "entry_time": df.iloc[position["entry_idx"]]["timestamp"],
                    "exit_time": row["timestamp"],
                })
                position = None

        current_equity = capital if position is None else position["size"] * price
        equity_curve.append(current_equity)

    return trades, equity_curve


def summarize(trades, equity_curve):
    if not trades:
        print("No se ejecutaron operaciones en el periodo analizado.")
        return

    df_trades = pd.DataFrame(trades)
    wins = df_trades[df_trades["pct_return"] > 0]
    losses = df_trades[df_trades["pct_return"] <= 0]

    final_equity = equity_curve[-1] if equity_curve else INITIAL_CAPITAL
    total_return = (final_equity / INITIAL_CAPITAL - 1) * 100

    equity_series = pd.Series(equity_curve)
    running_max = equity_series.cummax()
    drawdown = (equity_series - running_max) / running_max
    max_drawdown = drawdown.min() * 100

    print("=" * 50)
    print(f"Periodo analizado:   {df_trades['entry_time'].min()} -> {df_trades['exit_time'].max()}")
    print(f"Capital inicial:     ${INITIAL_CAPITAL:,.2f}")
    print(f"Capital final:       ${final_equity:,.2f}")
    print(f"Retorno total:       {total_return:.2f}%")
    print(f"Maximo drawdown:     {max_drawdown:.2f}%")
    print(f"N. operaciones:      {len(df_trades)}")
    print(f"Ganadoras:           {len(wins)} ({len(wins)/len(df_trades)*100:.1f}%)")
    print(f"Perdedoras:          {len(losses)} ({len(losses)/len(df_trades)*100:.1f}%)")
    if len(wins) > 0:
        print(f"Ganancia media:      {wins['pct_return'].mean()*100:.2f}%")
    if len(losses) > 0:
        print(f"Perdida media:       {losses['pct_return'].mean()*100:.2f}%")
    print("=" * 50)


if __name__ == "__main__":
    print(f"Descargando datos historicos de {SYMBOL} ({TIMEFRAME})...")
    df = fetch_ohlcv(SYMBOL, TIMEFRAME, LOOKBACK_CANDLES)
    print(f"{len(df)} velas descargadas. Calculando indicadores...")
    df = compute_indicators(df)
    print("Ejecutando backtest...")
    trades, equity_curve = run_backtest(df)
    summarize(trades, equity_curve)
