"""Health check � WebSocket + REST freshness."""
from __future__ import annotations
import time

E_CHECK = "[OK]"
E_CROSS = "[FAIL]"


def check_ws_health(ws_manager, max_stale_sec: float = 120.0) -> dict:
    stats = ws_manager.stats()
    healthy = ws_manager.is_healthy(max_stale_sec=max_stale_sec)
    return {
        "healthy": healthy,
        "mark_price": stats.get("mark_price"),
        "mark_age_sec": stats.get("last_mark_age_sec"),
        "kline_age_sec": stats.get("last_kline_age_sec"),
        "klines_count": stats.get("klines_count"),
        "error_count": stats.get("error_count"),
        "max_stale_sec": max_stale_sec,
    }


def format_health_report(health: dict) -> str:
    status = E_CHECK if health["healthy"] else E_CROSS
    mark_age = health.get("mark_age_sec")
    kline_age = health.get("kline_age_sec")

    def fmt_age(a):
        if a is None:
            return "never"
        return f"{a:.0f}s"

    return (
        f"{status} <b>WS Health</b>\n"
        f"Mark price: <code>{health.get('mark_price', 0):.2f}</code> "
        f"(age {fmt_age(mark_age)})\n"
        f"Kline age: {fmt_age(kline_age)}\n"
        f"Klines buffered: {health.get('klines_count', 0)}\n"
        f"Errors: {health.get('error_count', 0)}"
    )


if __name__ == "__main__":
    class FakeWS:
        def stats(self):
            return {
                "mark_price": 78000.0,
                "last_mark_age_sec": 5,
                "last_kline_age_sec": 30,
                "klines_count": 200,
                "error_count": 0,
            }
        def is_healthy(self, max_stale_sec=120):
            return True

    h = check_ws_health(FakeWS())
    print("check_ws_health:", h["healthy"])
    print("format:", format_health_report(h)[:100])
