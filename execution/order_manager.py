"""Order manager � market + SL/TP bracket (LONG & SHORT, Algo API compatible)."""
from __future__ import annotations
from decimal import Decimal, ROUND_DOWN, ROUND_UP


def _to_dec(x):
    return Decimal(str(x))


def round_qty(qty: float, step: float, precision: int = 8) -> float:
    if step <= 0:
        return float(round(_to_dec(qty), precision))
    d_step = _to_dec(step)
    d_qty = _to_dec(qty)
    n = (d_qty / d_step).to_integral_value(rounding=ROUND_DOWN)
    return float((n * d_step).quantize(d_step))


def round_price(price: float, tick: float, mode: str = "nearest") -> float:
    if tick <= 0:
        return float(price)
    d_tick = _to_dec(tick)
    d_price = _to_dec(price)
    if mode == "up":
        n = (d_price / d_tick).to_integral_value(rounding=ROUND_UP)
    elif mode == "down":
        n = (d_price / d_tick).to_integral_value(rounding=ROUND_DOWN)
    else:
        n = (d_price / d_tick).to_integral_value()
    return float((n * d_tick).quantize(d_tick))


def open_long(client, symbol, qty, sl_price, tp_price, filters):
    q = round_qty(qty, filters["step_size"], filters["qty_precision"])
    if q <= 0:
        return {"ok": False, "error": "qty<=0 after rounding"}

    sl = round_price(sl_price, filters["tick_size"], "down")
    tp = round_price(tp_price, filters["tick_size"], "up")

    try:
        order = client.market_order(symbol, "BUY", q)
        print(f"[order] LONG opened qty={q} id={order.get('orderId')}")
    except Exception as e:
        return {"ok": False, "error": str(e)}

    sl_order = None
    try:
        sl_order = client._client.futures_create_order(
            symbol=symbol, side="SELL", type="STOP_MARKET",
            stopPrice=sl, quantity=q, reduceOnly=True,
            workingType="MARK_PRICE",
        )
        ident = sl_order.get("algoId") or sl_order.get("orderId")
        print(f"[order] SL set @ {sl} id={ident}")
    except Exception as e:
        print(f"[order] SL FAILED: {e} � emergency close")
        try:
            client.reduce_only_order(symbol, "SELL", q)
        except Exception as ee:
            print(f"[order] EMERGENCY CLOSE FAILED: {ee}")
        return {"ok": False, "error": f"SL failed: {e}"}

    tp_order = None
    warnings = []
    try:
        tp_order = client._client.futures_create_order(
            symbol=symbol, side="SELL", type="TAKE_PROFIT_MARKET",
            stopPrice=tp, quantity=q, reduceOnly=True,
            workingType="MARK_PRICE",
        )
        ident = tp_order.get("algoId") or tp_order.get("orderId")
        print(f"[order] TP set @ {tp} id={ident}")
    except Exception as e:
        warnings.append(f"TP: {e}")
        print(f"[order] TP FAILED: {e} (SL still OK)")

    return {"ok": True, "qty": q, "sl_price": sl, "tp_price": tp,
            "entry_order": order, "sl_order": sl_order,
            "tp_order": tp_order, "warnings": warnings}


def open_short(client, symbol, qty, sl_price, tp_price, filters):
    q = round_qty(qty, filters["step_size"], filters["qty_precision"])
    if q <= 0:
        return {"ok": False, "error": "qty<=0 after rounding"}

    sl = round_price(sl_price, filters["tick_size"], "up")
    tp = round_price(tp_price, filters["tick_size"], "down")

    try:
        order = client.market_order(symbol, "SELL", q)
        print(f"[order] SHORT opened qty={q} id={order.get('orderId')}")
    except Exception as e:
        return {"ok": False, "error": str(e)}

    sl_order = None
    try:
        sl_order = client._client.futures_create_order(
            symbol=symbol, side="BUY", type="STOP_MARKET",
            stopPrice=sl, quantity=q, reduceOnly=True,
            workingType="MARK_PRICE",
        )
        ident = sl_order.get("algoId") or sl_order.get("orderId")
        print(f"[order] SL set @ {sl} id={ident}")
    except Exception as e:
        print(f"[order] SL FAILED: {e} � emergency close")
        try:
            client.reduce_only_order(symbol, "BUY", q)
        except Exception as ee:
            print(f"[order] EMERGENCY CLOSE FAILED: {ee}")
        return {"ok": False, "error": f"SL failed: {e}"}

    tp_order = None
    warnings = []
    try:
        tp_order = client._client.futures_create_order(
            symbol=symbol, side="BUY", type="TAKE_PROFIT_MARKET",
            stopPrice=tp, quantity=q, reduceOnly=True,
            workingType="MARK_PRICE",
        )
        ident = tp_order.get("algoId") or tp_order.get("orderId")
        print(f"[order] TP set @ {tp} id={ident}")
    except Exception as e:
        warnings.append(f"TP: {e}")
        print(f"[order] TP FAILED: {e} (SL still OK)")

    return {"ok": True, "qty": q, "sl_price": sl, "tp_price": tp,
            "entry_order": order, "sl_order": sl_order,
            "tp_order": tp_order, "warnings": warnings}


def close_position(client, symbol, side: str = "LONG"):
    pos = client.get_position(symbol)
    if pos["amt"] == 0:
        try:
            for o in client._client.futures_get_open_algo_orders(symbol=symbol):
                client._client.futures_cancel_algo_order(symbol=symbol, algoId=o["algoId"])
        except Exception:
            pass
        return {"ok": True, "msg": "no position"}

    close_side = "SELL" if pos["amt"] > 0 else "BUY"
    qty = abs(pos["amt"])

    try:
        client.cancel_all(symbol)
    except Exception as e:
        print(f"[order] cancel_all regular: {e}")

    try:
        for o in client._client.futures_get_open_algo_orders(symbol=symbol):
            try:
                client._client.futures_cancel_algo_order(symbol=symbol, algoId=o["algoId"])
                print(f"[order] cancelled algoId={o['algoId']}")
            except Exception as e:
                print(f"[order] cancel algo err: {e}")
    except Exception as e:
        print(f"[order] fetch algo err: {e}")

    try:
        order = client.reduce_only_order(symbol, close_side, qty)
        print(f"[order] Position closed qty={qty}")
        return {"ok": True, "order": order}
    except Exception as e:
        print(f"[order] Close failed: {e}")
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    assert round_qty(0.0384615, 0.001, 3) == 0.038
    assert round_price(77750.04, 0.1, "down") == 77750.0
    assert round_price(77750.06, 0.1, "up") == 77750.1
    print("? round helpers OK")

    class FakeClient:
        def __init__(self):
            self.calls = []
            self._client = self
        def market_order(self, s, side, q):
            self.calls.append(("market", side, q)); return {"orderId": 1}
        def futures_create_order(self, **kw):
            self.calls.append(("bracket", kw.get("type"), kw.get("stopPrice"), kw.get("quantity"))); return {"algoId": len(self.calls) * 100}
        def reduce_only_order(self, s, side, q):
            self.calls.append(("reduce", side, q)); return {"orderId": 99}
        def cancel_all(self, s): pass
        def futures_get_open_algo_orders(self, symbol): return []
        def futures_cancel_algo_order(self, **kw): pass
        def get_position(self, s): return {"amt": 0.0, "side": "FLAT"}

    fc = FakeClient()
    flt = {"step_size": 0.001, "qty_precision": 3, "tick_size": 0.1, "price_precision": 1}

    r1 = open_long(fc, "BTCUSDT", 0.03846, 77750.04, 78500.06, flt)
    assert r1["ok"] and r1["qty"] == 0.038 and r1["sl_price"] == 77750.0 and r1["tp_price"] == 78500.1
    print(f"? open_long OK qty={r1['qty']} SL={r1['sl_price']} TP={r1['tp_price']}")

    fc2 = FakeClient()
    r2 = open_short(fc2, "BTCUSDT", 0.03846, 78500.04, 77750.06, flt)
    assert r2["ok"] and r2["qty"] == 0.038 and r2["sl_price"] == 78500.1 and r2["tp_price"] == 77750.0
    print(f"? open_short OK qty={r2['qty']} SL={r2['sl_price']} TP={r2['tp_price']}")

    print("\n?? order_manager PASS (LONG + SHORT)")
