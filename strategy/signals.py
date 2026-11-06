"""Signal logic � rule-based (RSI + BB + ADX + trend). LONG & SHORT."""
from __future__ import annotations
import config


def long_entry_signal(row: dict, debug: bool = False) -> tuple[bool, dict]:
    rsi = float(row.get("rsi", 50))
    bb_pos = float(row.get("bb_position", 0.5))
    adx = float(row.get("adx", 0))
    close = float(row.get("close", 0))
    ema_fast = float(row.get("ema_fast", close))
    ema_slow = float(row.get("ema_slow", close))
    atr = float(row.get("atr", 0))

    cond_rsi   = rsi < config.RSI_OVERSOLD           # oversold
    cond_bb    = bb_pos < 0.35                        # LONG: lebih longgar dari 0.15
    cond_adx   = adx >= config.ADX_THRESHOLD
    cond_trend = ema_fast > ema_slow
    cond_atr   = atr > 0

    signal = cond_rsi and cond_bb and cond_adx and cond_trend and cond_atr
    details = {"rsi": rsi, "bb_position": bb_pos, "adx": adx,
               "cond_rsi": cond_rsi, "cond_bb": cond_bb,
               "cond_adx": cond_adx, "cond_trend": cond_trend,
               "cond_atr": cond_atr}
    if debug:
        failed = [k for k, v in details.items() if k.startswith("cond_") and not v]
        if failed:
            print(f"[signal] LONG blocked by: {failed}")
    return signal, details


def short_entry_signal(row: dict, debug: bool = False) -> tuple[bool, dict]:
    rsi = float(row.get("rsi", 50))
    bb_pos = float(row.get("bb_position", 0.5))
    adx = float(row.get("adx", 0))
    close = float(row.get("close", 0))
    ema_fast = float(row.get("ema_fast", close))
    ema_slow = float(row.get("ema_slow", close))
    atr = float(row.get("atr", 0))

    cond_rsi   = rsi > config.RSI_OVERBOUGHT          # overbought
    cond_bb    = bb_pos > 0.65                        # SHORT: di atas upper BB
    cond_adx   = adx >= config.ADX_THRESHOLD
    cond_trend = ema_fast < ema_slow                  # downtrend
    cond_atr   = atr > 0

    signal = cond_rsi and cond_bb and cond_adx and cond_trend and cond_atr
    details = {"rsi": rsi, "bb_position": bb_pos, "adx": adx,
               "cond_rsi": cond_rsi, "cond_bb": cond_bb,
               "cond_adx": cond_adx, "cond_trend": cond_trend,
               "cond_atr": cond_atr}
    if debug:
        failed = [k for k, v in details.items() if k.startswith("cond_") and not v]
        if failed:
            print(f"[signal] SHORT blocked by: {failed}")
    return signal, details


def long_exit_signal(row: dict) -> bool:
    rsi = float(row.get("rsi", 50))
    bb_pos = float(row.get("bb_position", 0.5))
    return rsi > config.RSI_OVERBOUGHT or bb_pos > 0.85


def short_exit_signal(row: dict) -> bool:
    rsi = float(row.get("rsi", 50))
    bb_pos = float(row.get("bb_position", 0.5))
    return rsi < config.RSI_OVERSOLD or bb_pos < 0.15
