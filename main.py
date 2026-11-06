"""Main entry point � Futures bot (anti-ban, LONG + SHORT, hybrid emoji)."""
import sys
import os
import time
import signal
import json

sys.path.insert(0, "/home/admin/bots/btc_bot")
os.chdir("/home/admin/bots/btc_bot")

import config
from core.websocket_manager import get_ws_manager
from core.binance_client import get_client
from strategy.indicators import add_indicators
from strategy.signals import (
    long_entry_signal, long_exit_signal,
    short_entry_signal, short_exit_signal,
)
from risk.manager import RiskManager
from execution.order_manager import open_long, open_short, close_position
from monitoring.logger import get_logger
from monitoring.telegram import (
    send, E_GREEN, E_RED, E_WARN, E_STOP, E_ROBOT, E_CHECK, E_LINE,
)
from monitoring.health import check_ws_health, format_health_report

log = get_logger("main")

_shutdown = False
STATE_FILE = "/home/admin/bots/btc_bot/data/state.json"

def _handle_signal(sig, frame):
    global _shutdown
    log.warning(f"Received signal {sig} � shutting down")
    _shutdown = True

signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


# ===== FUNGSI STATE (PnL KUMULATIF) =====
def load_state() -> dict:
    """Memuat data PnL kumulatif dari file JSON."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            log.error(f"Failed to load state: {e}")
    return {"total_pnl": 0.0, "total_trades": 0}

def save_state(state: dict):
    """Menyimpan data PnL kumulatif ke file JSON."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
    except Exception as e:
        log.error(f"Failed to save state: {e}")
# =========================================


def _klines_from_ws_to_df(klines: list):
    import pandas as pd
    if not klines:
        return None
    df = pd.DataFrame(klines)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df = df.set_index("open_time")
    return df[["open", "high", "low", "close", "volume"]]


def main():
    log.info("=" * 60)
    log.info(f"Futures bot START � testnet={config.FUTURES_TESTNET}")
    log.info(f"Symbol={config.SYMBOL} interval={config.INTERVAL} leverage={config.LEVERAGE}")
    log.info("=" * 60)

    # Load state kumulatif
    state = load_state()
    log.info(f"Loaded State: Total PnL=${state.get('total_pnl', 0):.2f} | Trades={state.get('total_trades', 0)}")

    ws = get_ws_manager()
    try:
        ws.start(wait_ready=True, timeout=60)
    except Exception as e:
        log.exception(f"WS start failed: {e}")
        send(f"{E_STOP} <b>WS start FAILED</b>: {e}")
        return

    send(
        f"{E_ROBOT} <b>Bot start</b>\n"
        f"Symbol: <code>{config.SYMBOL}</code>\n"
        f"Interval: <code>{config.INTERVAL}</code>\n"
        f"Leverage: <code>{config.LEVERAGE}x</code>\n"
        f"Testnet: <code>{config.FUTURES_TESTNET}</code>\n"
        f"Mark price: <code>{ws.get_mark_price():.2f}</code>\n"
        f"Total PnL: <code>{state.get('total_pnl', 0):+.2f}</code> ({state.get('total_trades', 0)} trades)"
    )

    try:
        client = get_client()
    except Exception as e:
        log.exception(f"REST client failed: {e}")
        send(f"{E_STOP} <b>REST client FAILED</b>: {e}")
        ws.stop()
        return

    try:
        client.setup_symbol(config.SYMBOL, config.LEVERAGE, config.MARGIN_TYPE)
        filters = client.get_symbol_filters(config.SYMBOL)
        log.info(f"Filters: {filters}")

        _seed = client.get_klines(config.SYMBOL, config.INTERVAL, limit=200)
        with ws._lock:
            ws.klines = [
                {
                    "open_time": int(k[0]), "close_time": int(k[6]),
                    "open": float(k[1]), "high": float(k[2]), "low": float(k[3]),
                    "close": float(k[4]), "volume": float(k[5]),
                    "is_closed": True,
                }
                for k in _seed
            ]
        log.info(f"Seeded {len(ws.klines)} klines from REST")
    except Exception as e:
        log.exception(f"Setup failed: {e}")
        send(f"{E_STOP} <b>Setup FAILED</b>: {e}")
        ws.stop()
        return

    try:
        eq = client.get_equity()
        pos = client.get_position(config.SYMBOL)
        log.info(f"Init equity={eq:.2f} position={pos}")
        risk = RiskManager(eq)
    except Exception as e:
        log.exception(f"Snapshot failed: {e}")
        send(f"{E_STOP} <b>Snapshot FAILED</b>: {e}")
        ws.stop()
        return

    if pos["amt"] != 0:
        log.warning(f"Existing position found: {pos}")
        send(
            f"{E_WARN} <b>Recovery</b>: posisi existing\n"
            f"Side: {pos['side']}\n"
            f"Amt: <code>{pos['amt']}</code>\n"
            f"Entry: <code>{pos['entry_price']:.2f}</code>\n"
            f"uPnL: <code>{pos['unrealized_pnl']:+.2f} USDT</code>\n"
            f"{E_LINE * 14}\n"
            f"Equity: <code>${eq:.2f}</code>"
        )

    last_health_check = 0
    loop_count = 0

    while not _shutdown:
        try:
            loop_count += 1
            mark = ws.get_mark_price()
            if mark <= 0:
                log.warning("Mark price not ready � skip")
                time.sleep(5)
                continue

            now = time.time()
            if now - last_health_check > 300:
                h = check_ws_health(ws, max_stale_sec=120)
                log.info(f"Health: {h}")
                if not h["healthy"]:
                    log.error("WS unhealthy � send alert")
                    send(f"{E_WARN} {format_health_report(h)}")
                last_health_check = now

            klines = ws.get_klines(limit=200)
            if len(klines) < 60:
                log.info(f"Klines buffer={len(klines)} < 60 � wait")
                time.sleep(60)
                continue

            df = _klines_from_ws_to_df(klines)
            df = add_indicators(df)
            row = df.iloc[-1].to_dict()

            eq_total = client.get_equity()
            pos = client.get_position(config.SYMBOL)
            risk.update_equity(eq_total)

            if risk.daily_loss_exceeded():
                if risk.should_alert_daily_limit():
                    loss_pct = (risk.equity_start_day - eq_total) / risk.equity_start_day * 100
                    loss_usd = risk.equity_start_day - eq_total
                    log.warning(f"Daily loss HIT: -{loss_pct:.2f}%")
                    send(
                        f"{E_STOP} <b>Daily loss limit</b>\n"
                        f"Loss: <code>-{loss_usd:.2f}</code> (-{loss_pct:.2f}%)\n"
                        f"{E_LINE * 14}\n"
                        f"Equity awal: <code>${risk.equity_start_day:.2f}</code>\n"
                        f"Equity now: <code>${eq_total:.2f}</code>\n"
                        f"<b>No new trades today.</b>"
                    )
                else:
                    log.warning("Daily loss limit (already alerted)")
                time.sleep(60)
                continue

            log.info(
                f"loop={loop_count} mark={mark:.2f} close={row['close']:.2f} "
                f"rsi={row['rsi']:.1f} bb_pos={row['bb_position']:.2f} "
                f"adx={row['adx']:.1f} eq={eq_total:.2f} pos={pos['side']} amt={pos['amt']}"
            )

            long_sig, _ = long_entry_signal(row, debug=False)
            short_sig, _ = (short_entry_signal(row, debug=False)
                            if config.ENABLE_SHORT else (False, {}))
            long_exit = long_exit_signal(row)
            short_exit = short_exit_signal(row)

            # Entry LONG
            if long_sig and pos["side"] == "FLAT":
                qty = risk.position_size(row["close"], row["atr"])
                notional = qty * mark
                if qty <= 0:
                    log.warning(f"Skip LONG: qty=0")
                elif qty < filters["min_qty"]:
                    log.warning(f"Skip LONG: qty={qty:.6f} < min={filters['min_qty']}")
                elif notional < filters["min_notional"]:
                    log.warning(f"Skip LONG: notional=${notional:.2f} < min=${filters['min_notional']}")
                else:
                    sl, tp = risk.sl_tp(row["close"], row["atr"], "LONG")
                    rr = (tp - row["close"]) / (row["close"] - sl) if (row["close"] - sl) > 0 else 0
                    log.info(f"-> LONG qty={qty:.6f} notional=${notional:.2f} SL={sl:.2f} TP={tp:.2f}")
                    result = open_long(client, config.SYMBOL, qty, sl, tp, filters)
                    if result["ok"]:
                        warn_txt = ""
                        if result.get("warnings"):
                            warn_txt = f"\n{E_WARN} {'; '.join(result['warnings'])}"
                        eq_now = client.get_equity()
                        send(
                            f"{E_GREEN} <b>LONG</b> {config.SYMBOL}\n"
                            f"Qty: <code>{result['qty']:.6f}</code> (${notional:.2f})\n"
                            f"Entry: <code>{mark:.2f}</code>\n"
                            f"SL: <code>{result['sl_price']:.2f}</code> ({((result['sl_price']-mark)/mark*100):+.2f}%)\n"
                            f"TP: <code>{result['tp_price']:.2f}</code> ({((result['tp_price']-mark)/mark*100):+.2f}%)\n"
                            f"R:R = <code>1:{rr:.2f}</code>\n"
                            f"{E_LINE * 14}\n"
                            f"Equity: <code>${eq_now:.2f}</code>"
                            f"{warn_txt}"
                        )
                    else:
                        log.error(f"LONG failed: {result.get('error')}")
                        send(f"{E_WARN} LONG rejected: {result.get('error')}")

            # Entry SHORT
            elif short_sig and pos["side"] == "FLAT":
                qty = risk.position_size(row["close"], row["atr"])
                notional = qty * mark
                if qty <= 0:
                    log.warning(f"Skip SHORT: qty=0")
                elif qty < filters["min_qty"]:
                    log.warning(f"Skip SHORT: qty={qty:.6f} < min={filters['min_qty']}")
                elif notional < filters["min_notional"]:
                    log.warning(f"Skip SHORT: notional=${notional:.2f} < min=${filters['min_notional']}")
                else:
                    sl, tp = risk.sl_tp(row["close"], row["atr"], "SHORT")
                    rr = (row["close"] - tp) / (sl - row["close"]) if (sl - row["close"]) > 0 else 0
                    log.info(f"-> SHORT qty={qty:.6f} notional=${notional:.2f} SL={sl:.2f} TP={tp:.2f}")
                    result = open_short(client, config.SYMBOL, qty, sl, tp, filters)
                    if result["ok"]:
                        warn_txt = ""
                        if result.get("warnings"):
                            warn_txt = f"\n{E_WARN} {'; '.join(result['warnings'])}"
                        eq_now = client.get_equity()
                        send(
                            f"{E_RED} <b>SHORT</b> {config.SYMBOL}\n"
                            f"Qty: <code>{result['qty']:.6f}</code> (${notional:.2f})\n"
                            f"Entry: <code>{mark:.2f}</code>\n"
                            f"SL: <code>{result['sl_price']:.2f}</code> ({((result['sl_price']-mark)/mark*100):+.2f}%)\n"
                            f"TP: <code>{result['tp_price']:.2f}</code> ({((result['tp_price']-mark)/mark*100):+.2f}%)\n"
                            f"R:R = <code>1:{rr:.2f}</code>\n"
                            f"{E_LINE * 14}\n"
                            f"Equity: <code>${eq_now:.2f}</code>"
                            f"{warn_txt}"
                        )
                    else:
                        log.error(f"SHORT failed: {result.get('error')}")
                        send(f"{E_WARN} SHORT rejected: {result.get('error')}")

            # Exit
            elif ((pos["side"] == "LONG" and long_exit) or
                  (pos["side"] == "SHORT" and short_exit)):
                entry_price = pos["entry_price"]
                entry_amt = pos["amt"]
                log.info(f"-> CLOSE {pos['side']} amt={entry_amt} entry={entry_price:.2f}")
                res = close_position(client, config.SYMBOL, pos["side"])
                
                if res["ok"]:
                    pnl_usd = pos["unrealized_pnl"]
                    pnl_pct = (pnl_usd / (abs(entry_amt) * entry_price) * 100) if entry_price > 0 else 0
                    eq_now = client.get_equity()
                    eq_start = risk.equity_start_day
                    day_pnl = eq_now - eq_start
                    day_pct = (day_pnl / eq_start * 100) if eq_start > 0 else 0
                    
                    # UPDATE PnL KUMULATIF
                    state["total_pnl"] = state.get("total_pnl", 0.0) + pnl_usd
                    state["total_trades"] = state.get("total_trades", 0) + 1
                    save_state(state)
                    
                    head_emoji = E_GREEN if pnl_usd >= 0 else E_RED
                    send(
                        f"{head_emoji} <b>CLOSE {pos['side']}</b> {config.SYMBOL}\n"
                        f"Entry: <code>{entry_price:.2f}</code> -> Exit: <code>{mark:.2f}</code>\n"
                        f"Qty: <code>{abs(entry_amt):.6f}</code>\n"
                        f"{E_LINE * 14}\n"
                        f"PnL Trade: <code>{pnl_usd:+.2f}</code> ({pnl_pct:+.2f}%)\n"
                        f"PnL Harian: <code>{day_pnl:+.2f}</code> ({day_pct:+.2f}%)\n"
                        f"{E_LINE * 14}\n"
                        f"Equity: <code>${eq_now:.2f}</code>\n"
                        f"Total PnL: <code>{state['total_pnl']:+.2f}</code> ({state['total_trades']} trades)"
                    )
                else:
                    log.error(f"Close failed: {res.get('error')}")
                    send(f"{E_STOP} CLOSE failed: {res.get('error')}")

            time.sleep(config.POLL_INTERVAL_SEC)

        except KeyboardInterrupt:
            break
        except Exception as e:
            log.exception(f"Loop error: {e}")
            send(f"{E_WARN} Loop error: <code>{str(e)[:200]}</code>")
            time.sleep(30)

    log.info("Shutting down...")
    send(f"{E_WARN} Bot stopped")
    ws.stop()
    log.info("Bye.")


if __name__ == "__main__":
    main()
