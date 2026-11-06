"""Binance Futures REST client dengan rate limiter built-in."""
from __future__ import annotations
import time
import re
from typing import Any, Optional

from binance.client import Client
from binance.exceptions import BinanceAPIException

import config
from core.rate_limiter import get_limiter, WEIGHT_MAP


MAX_RETRIES = 3
RETRY_BACKOFF_SEC = [2, 5, 10]


class RateLimitedClient:
    """Wrapper Client � semua request lewat rate limiter."""

    def __init__(self):
        self._client = Client(
            config.FUTURES_API_KEY,
            config.FUTURES_API_SECRET,
            testnet=config.FUTURES_TESTNET,
        )
        self._limiter = get_limiter()
        self._sync_time()
        self._check_position_mode()

    def _sync_time(self):
        try:
            server_time = self._client.futures_time()["serverTime"]
            local_time = int(time.time() * 1000)
            self._client.timestamp_offset = server_time - local_time
            print(f"[client] clock offset={self._client.timestamp_offset}ms")
        except Exception as e:
            print(f"[client] clock sync failed: {e}")

    def _check_position_mode(self):
        try:
            mode = self._client.futures_get_position_mode()
            if mode.get("dualSidePosition"):
                print("[client] ?? HEDGE mode � set one-way di Binance UI")
            else:
                print("[client] ? One-way mode")
        except Exception as e:
            print(f"[client] position mode check failed: {e}")

    def _weight_for(self, method: str, kwargs: dict) -> int:
        base = WEIGHT_MAP.get(method, 1)
        if method == "futures_klines":
            limit = kwargs.get("limit", 500)
            if limit <= 100:
                return 1
            elif limit <= 500:
                return 2
            elif limit <= 1000:
                return 5
            else:
                return 10
        return base

    def _handle_ban(self, err: BinanceAPIException) -> bool:
        if err.code == -1003:
            msg = err.message
            match = re.search(r"banned until (\d+)", msg)
            if match:
                self._limiter.record_ban(int(match.group(1)))
                return True
            print("[client] ? -1003 tanpa ban_until, sleep 60s")
            time.sleep(60)
            return True
        return False

    def _call(self, method_name: str, **kwargs) -> Any:
        for attempt in range(MAX_RETRIES + 1):
            weight = self._weight_for(method_name, kwargs)
            self._limiter.acquire(weight=weight, timeout=120)
            try:
                method = getattr(self._client, method_name)
                return method(**kwargs)
            except BinanceAPIException as e:
                if self._handle_ban(e):
                    if attempt < MAX_RETRIES:
                        continue
                    raise
                retryable = e.code in (-1001, -1007, -1008)
                if retryable and attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF_SEC[attempt]
                    print(f"[client] {method_name} err {e.code}, retry {attempt+1}/{MAX_RETRIES} in {wait}s")
                    time.sleep(wait)
                    continue
                raise
            except Exception as e:
                if attempt < MAX_RETRIES:
                    wait = RETRY_BACKOFF_SEC[attempt]
                    print(f"[client] {method_name} exception: {e}, retry in {wait}s")
                    time.sleep(wait)
                    continue
                raise
        raise RuntimeError(f"{method_name} failed after {MAX_RETRIES} retries")

    def ping(self):
        return self._call("futures_ping")

    def get_balance(self, asset: str = "USDT") -> float:
        """Mengambil saldo wallet (tidak termasuk PnL floating)."""
        balances = self._call("futures_account_balance")
        for b in balances:
            if b["asset"] == asset:
                return float(b["balance"])
        return 0.0

    def get_equity(self) -> float:
        """Mengambil Total Margin Balance (Saldo Aset + PnL floating) akurat seperti di Binance."""
        acc = self._call("futures_account")
        return float(acc["totalMarginBalance"])

    def get_position(self, symbol: str) -> dict:
        positions = self._call("futures_position_information", symbol=symbol)
        for p in positions:
            if p["symbol"] == symbol:
                amt = float(p["positionAmt"])
                return {
                    "amt": amt,
                    "entry_price": float(p.get("entryPrice", 0) or 0),
                    "unrealized_pnl": float(p.get("unRealizedProfit", 0) or 0),
                    "side": "LONG" if amt > 0 else ("SHORT" if amt < 0 else "FLAT"),
                    "leverage": int(p.get("leverage", 0) or 0),
                }
        return {"amt": 0.0, "entry_price": 0.0, "unrealized_pnl": 0.0,
                "side": "FLAT", "leverage": 0}

    def get_mark_price(self, symbol: str) -> float:
        m = self._call("futures_mark_price", symbol=symbol)
        return float(m["markPrice"])

    def get_klines(self, symbol: str, interval: str = "1h", limit: int = 200) -> list:
        return self._call("futures_klines", symbol=symbol, interval=interval, limit=limit)

    def get_exchange_info(self):
        return self._call("futures_exchange_info")

    def get_symbol_filters(self, symbol: str) -> dict:
        info = self.get_exchange_info()
        for s in info["symbols"]:
            if s["symbol"] == symbol:
                filters = {f["filterType"]: f for f in s["filters"]}
                return {
                    "step_size": float(filters["LOT_SIZE"]["stepSize"]),
                    "min_qty": float(filters["LOT_SIZE"]["minQty"]),
                    "tick_size": float(filters["PRICE_FILTER"]["tickSize"]),
                    "min_notional": float(
                        filters.get("MIN_NOTIONAL", {}).get("notional", 5.0)
                    ),
                    "price_precision": int(s["pricePrecision"]),
                    "qty_precision": int(s["quantityPrecision"]),
                }
        raise ValueError(f"Symbol {symbol} not found")

    def setup_symbol(self, symbol: str, leverage: int, margin_type: str):
        try:
            self._limiter.acquire(weight=1)
            self._client.futures_change_leverage(symbol=symbol, leverage=leverage)
            print(f"[client] leverage={leverage}x OK for {symbol}")
        except BinanceAPIException as e:
            print(f"[client] leverage error: {e.code} {e.message}")

        try:
            self._limiter.acquire(weight=1)
            self._client.futures_change_margin_type(symbol=symbol, marginType=margin_type)
            print(f"[client] margin={margin_type} OK for {symbol}")
        except BinanceAPIException as e:
            if e.code == -4046:
                print(f"[client] margin={margin_type} already set")
            else:
                print(f"[client] margin error: {e.code} {e.message}")

    def market_order(self, symbol: str, side: str, qty: float) -> dict:
        return self._call(
            "futures_create_order",
            symbol=symbol, side=side, type="MARKET", quantity=qty,
        )

    def reduce_only_order(self, symbol: str, side: str, qty: float) -> dict:
        return self._call(
            "futures_create_order",
            symbol=symbol, side=side, type="MARKET",
            quantity=qty, reduceOnly=True,
        )

    def get_open_orders(self, symbol: str) -> list:
        return self._call("futures_get_open_orders", symbol=symbol)

    def cancel_all(self, symbol: str):
        return self._call("futures_cancel_all_open_orders", symbol=symbol)

    def stats(self) -> dict:
        return self._limiter.stats()


_client_instance: Optional[RateLimitedClient] = None


def get_client() -> RateLimitedClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = RateLimitedClient()
    return _client_instance
