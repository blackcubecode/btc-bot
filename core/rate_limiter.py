"""Rate limiter untuk Binance API � anti-ban.

Binance Futures rate limit:
- 2400 weight/menit per IP (REST)
- 1200 weight/menit untuk order endpoints
- 300 weight/5 menit untuk beberapa endpoint

File ini track weight secara global (per process) dan throttle request
sebelum kena limit, plus exponential backoff saat kena -1003.
"""
from __future__ import annotations
import time
import threading
from collections import deque
from typing import Optional


# ===== Weight map endpoint Binance Futures =====
# https://binance-docs.github.io/apidocs/futures/en/#general-info
WEIGHT_MAP = {
    "futures_ping": 1,
    "futures_time": 1,
    "futures_exchange_info": 1,
    "futures_klines": 1,          # limit <= 100; 2 untuk 101-500; 5 untuk 501-1000; 10 untuk >1000
    "futures_mark_price": 1,
    "futures_ticker_price": 1,
    "futures_account_balance": 5,
    "futures_position_information": 5,
    "futures_get_open_orders": 1,
    "futures_create_order": 1,
    "futures_cancel_all_open_orders": 1,
    "futures_change_leverage": 1,
    "futures_change_margin_type": 1,
    "futures_get_position_mode": 1,
}

# Batas konservatif (50% dari limit Binance = aman)
DEFAULT_WEIGHT_LIMIT = 1200     # per minute (dari 2400)
DEFAULT_WINDOW_SEC = 60


class RateLimiter:
    """Sliding-window rate limiter berbasis weight."""

    def __init__(
        self,
        weight_limit: int = DEFAULT_WEIGHT_LIMIT,
        window_sec: int = DEFAULT_WINDOW_SEC,
        safety_margin: float = 0.9,
    ):
        """
        Args:
            weight_limit: max weight per window (konservatif: 1200, bukan 2400)
            window_sec: panjang window (detik)
            safety_margin: gunakan hanya 90% dari limit
        """
        self.weight_limit = int(weight_limit * safety_margin)
        self.window_sec = window_sec
        self._events: deque[tuple[float, int]] = deque()  # (timestamp, weight)
        self._lock = threading.Lock()
        self._total_requests = 0
        self._total_weight = 0
        self._total_waits = 0

    def _cleanup(self, now: float):
        """Buang event yang sudah di luar window."""
        cutoff = now - self.window_sec
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()

    def _current_weight(self, now: float) -> int:
        self._cleanup(now)
        return sum(w for _, w in self._events)

    def acquire(self, weight: int = 1, timeout: Optional[float] = None):
        """Block sampai weight tersedia, lalu catat penggunaan.

        Args:
            weight: weight request yang akan dilakukan
            timeout: max detik untuk wait. None = tunggu sampai dapat.

        Raises:
            TimeoutError: kalau timeout tercapai sebelum weight tersedia.
        """
        start = time.time()
        with self._lock:
            while True:
                now = time.time()
                current = self._current_weight(now)

                # Cukup?
                if current + weight <= self.weight_limit:
                    self._events.append((now, weight))
                    self._total_requests += 1
                    self._total_weight += weight
                    return

                # Hitung berapa lama harus tunggu
                # Buang event sampai weight cukup
                needed = current + weight - self.weight_limit
                freed = 0
                wait_until = now
                for ts, w in self._events:
                    freed += w
                    wait_until = ts + self.window_sec
                    if freed >= needed:
                        break

                wait_sec = max(0.1, wait_until - now + 0.05)
                self._total_waits += 1

                # Timeout?
                if timeout is not None:
                    elapsed = time.time() - start
                    if elapsed + wait_sec > timeout:
                        raise TimeoutError(
                            f"Rate limiter timeout: need {weight} weight, "
                            f"current={current}, limit={self.weight_limit}, "
                            f"waited {elapsed:.1f}s"
                        )

                print(
                    f"[rate_limiter] Throttling: need {weight} weight, "
                    f"current={current}/{self.weight_limit}, "
                    f"wait {wait_sec:.1f}s"
                )
                time.sleep(wait_sec)

    def record_ban(self, ban_until_ms: int):
        """Kalau kena -1003, paksa tunggu sampai ban lewat."""
        ban_until = ban_until_ms / 1000
        now = time.time()
        wait = ban_until - now
        if wait > 0:
            print(
                f"[rate_limiter] ? BANNED until "
                f"{time.strftime('%H:%M:%S', time.localtime(ban_until))} "
                f"({int(wait)}s) � sleeping..."
            )
            time.sleep(wait + 2)  # +2s buffer

    def stats(self) -> dict:
        """Statistik untuk monitoring."""
        now = time.time()
        return {
            "current_weight": self._current_weight(now),
            "weight_limit": self.weight_limit,
            "window_sec": self.window_sec,
            "total_requests": self._total_requests,
            "total_weight": self._total_weight,
            "total_waits": self._total_waits,
        }


# ===== Global singleton =====
_limiter: Optional[RateLimiter] = None
_limiter_lock = threading.Lock()


def get_limiter() -> RateLimiter:
    """Ambil global rate limiter (thread-safe singleton)."""
    global _limiter
    if _limiter is None:
        with _limiter_lock:
            if _limiter is None:
                _limiter = RateLimiter()
    return _limiter
