"""Telegram alert � hybrid (emoji header only)."""
import os
import requests
from dotenv import load_dotenv

load_dotenv("/home/admin/bots/btc_bot/.env")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHATS = [c.strip() for c in os.getenv("TELEGRAM_CHAT_ID", "").split(",") if c.strip()]

# ==== Emoji header (Unicode-safe) ====
E_GREEN   = "\U0001F7E2"   # ??
E_RED     = "\U0001F534"   # ??
E_WARN    = "\u26A0\uFE0F" # ??
E_STOP    = "\U0001F6D1"   # ??
E_ROBOT   = "\U0001F916"   # ??
E_CHECK   = "\u2705"       # ?
E_CROSS   = "\u274C"       # ?
E_LINE    = "\u2501"       # ?

# Alias biar import lama tetap jalan
E_LONG  = E_GREEN
E_SHORT = E_RED


def send(msg: str, silent: bool = False) -> bool:
    if not TOKEN or not CHATS:
        print("[tg] TOKEN/CHAT kosong � skip")
        return False
    all_ok = True
    for chat_id in CHATS:
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": msg,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                    "disable_notification": silent,
                },
                timeout=10,
            )
            if r.status_code != 200:
                print(f"[tg] chat {chat_id} -> HTTP {r.status_code}: {r.text[:200]}")
                all_ok = False
        except Exception as e:
            print(f"[tg] chat {chat_id} error: {e}")
            all_ok = False
    return all_ok


if __name__ == "__main__":
    print(f"Chats: {CHATS}")
    ok = send(f"{E_ROBOT} <b>Test hybrid</b> {E_CHECK}")
    print(f"Send result: {ok}")
