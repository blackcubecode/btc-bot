"""WebSocket manager untuk Binance Futures � anti-ban.

Stream yang dipakai:
- markPrice@1s     : harga mark real-time (untuk SL/TP & signal)
- kline_<interval> : candle update (untuk indikator)

WebSocket TIDAK dihitung dalam rate limit REST (2400 weight/menit).
Connect 24 jam = 1 koneksi. Ini cara utama menghindari ban.
"""
from __future__ import annotations
import json
import threading
import time
from typing import Callable, Optional

from binance import ThreadedWebsocketManager

import config


# ===== URL selector =====
def _ws_url() -> str:
    if config.FUTURES_TESTNET:
        return "wss://stream.binancefuture.com"
    return "wss://fstream.binance.com"


class WSManager:
    """Manager untuk Binance Futures WebSocket streams.

    Menyimpan state terakhir:
    - mark_price   : float (harga mark terbaru)
    - klines       : list[dict] (buffer candle, terbaru di akhir)
    - last_update  : timestamp update terakhir (untuk health check)
    """

    def __init__(self, symbol: str, interval: str = "1h"):
        self.symbol = symbol.upper()
        self.interval = interval

        self.mark_price: float = 0.0
        self.klines: list[dict] = []           # buffer candle
        self.kline_maxlen: int = 300

        self.last_mark_ts: float = 0.0
        self.last_kline_ts: float = 0.0
        self.last_msg_ts: float = 0.0

        self._lock = threading.Lock()
        self._twm: Optional[ThreadedWebsocketManager] = None
        self._connected = False
        self._error_count = 0

        # Callbacks (opsional)
        self.on_mark_price: Optional[Callable[[float], None]] = None
        self.on_kline_close: Optional[Callable[[dict], None]] = None

    # ===== Lifecycle =====

    def start(self, wait_ready: bool = True, timeout: float = 30.0):
        print(f"[ws] Starting WS for {self.symbol} {self.interval}")
        self._twm = ThreadedWebsocketManager(
            api_key=config.FUTURES_API_KEY,
            api_secret=config.FUTURES_API_SECRET,
            testnet=config.FUTURES_TESTNET,
        )
        self._twm.start()
        mark_stream = f"{self.symbol.lower()}@markPrice@1s"
        self._twm.start_futures_multiplex_socket(
            streams=[mark_stream],
            callback=self._handle_mark_price,
        )
        self._twm.start_kline_futures_socket(
            symbol=self.symbol, interval=self.interval,
            callback=self._handle_kline,
        )
        if wait_ready:
            start = time.time()
            while time.time() - start < timeout:
                with self._lock:
                    if self.mark_price > 0 and self.klines:
                        self._connected = True
                        print(f"[ws] Ready mark={self.mark_price:.2f} klines={len(self.klines)}")
                        return
                time.sleep(0.5)
            raise TimeoutError(f"WS not ready: mark={self.mark_price} klines={len(self.klines)}")

    def stop(self):
        """Stop semua stream + disconnect."""
        if self._twm:
            try:
                self._twm.stop()
                print("[ws] Stopped")
            except Exception as e:
                print(f"[ws] Stop error: {e}")
            self._twm = None
        self._connected = False

    # ===== Handlers =====

    def _handle_mark_price(self, msg: dict):
        try:
            data = msg.get("data", msg)
            if data.get("e") != "markPriceUpdate":
                return
            price = float(data["p"])
            with self._lock:
                self.mark_price = price
                self.last_mark_ts = time.time()
                self.last_msg_ts = self.last_mark_ts
            if self.on_mark_price:
                self.on_mark_price(price)
        except Exception as e:
            self._error_count += 1
            print(f"[ws] mark handler error: {e}")

    def _handle_kline(self, msg: dict):
        """Handler kline stream."""
        try:
            k = msg.get("k", {})
            if not k:
                return

            candle = {
                "open_time": int(k["t"]),
                "close_time": int(k["T"]),
                "open": float(k["o"]),
                "high": float(k["h"]),
                "low": float(k["l"]),
                "close": float(k["c"]),
                "volume": float(k["v"]),
                "is_closed": bool(k["x"]),
            }

            with self._lock:
                # Update candle terakhir kalau open_time sama
                if self.klines and self.klines[-1]["open_time"] == candle["open_time"]:
                    self.klines[-1] = candle
                else:
                    self.klines.append(candle)
                    # Trim buffer
                    if len(self.klines) > self.kline_maxlen:
                        self.klines = self.klines[-self.kline_maxlen:]

                self.last_kline_ts = time.time()
                self.last_msg_ts = self.last_kline_ts

            # Callback hanya saat candle close (untuk signal)
            if candle["is_closed"] and self.on_kline_close:
                try:
                    self.on_kline_close(candle)
                except Exception as e:
                    print(f"[ws] on_kline_close callback error: {e}")

        except Exception as e:
            self._error_count += 1
            print(f"[ws] kline handler error: {e}")

    # ===== Accessors =====

    def get_mark_price(self) -> float:
        with self._lock:
            return self.mark_price

    def get_klines(self, limit: int = 200) -> list[dict]:
        """Ambil buffer candle terakhir (copy)."""
        with self._lock:
            return list(self.klines[-limit:])

    def is_healthy(self, max_stale_sec: float = 120.0) -> bool:
        """Cek koneksi masih fresh (tidak stale)."""
        with self._lock:
            if self.last_msg_ts == 0:
                return False
            age = time.time() - self.last_msg_ts
            return age < max_stale_sec

    def stats(self) -> dict:
        with self._lock:
            return {
                "connected": self._connected,
                "mark_price": self.mark_price,
                "klines_count": len(self.klines),
                "last_mark_age_sec": (
                    time.time() - self.last_mark_ts if self.last_mark_ts else None
                ),
                "last_kline_age_sec": (
                    time.time() - self.last_kline_ts if self.last_kline_ts else None
                ),
                "error_count": self._error_count,
            }


# ===== Singleton =====
_ws_instance: Optional[WSManager] = None


def get_ws_manager() -> WSManager:
    global _ws_instance
    if _ws_instance is None:
        _ws_instance = WSManager(symbol=config.SYMBOL, interval=config.INTERVAL)
    return _ws_instance


if __name__ == "__main__":
    # Smoke test � akan connect & stream 10 detik (JANGAN dijalankan saat ban!)
    print("?? Smoke test akan connect ke Binance WS")
    print("   Jalankan hanya setelah ban clear!\n")

    ws = get_ws_manager()
    ws.start()
    print("\nStreaming 10 detik...")
    for i in range(10):
        time.sleep(1)
        print(
            f"  t={i+1}s mark={ws.get_mark_price():.2f} "
            f"klines={len(ws.get_klines())} "
            f"healthy={ws.is_healthy()}"
        )
    print("\nStats:", ws.stats())
    ws.stop()
