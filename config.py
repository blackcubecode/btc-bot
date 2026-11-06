"""Konfigurasi global bot � FUTURES ONLY."""
import os
from dotenv import load_dotenv

load_dotenv("/home/admin/bots/btc_bot/.env")

# ------- API -------
FUTURES_API_KEY    = os.getenv("BINANCE_FUTURES_API_KEY")
FUTURES_API_SECRET = os.getenv("BINANCE_FUTURES_API_SECRET")
FUTURES_TESTNET    = os.getenv("BINANCE_FUTURES_TESTNET", "true").lower() == "true"

# ------- Market -------
SYMBOL   = os.getenv("SYMBOL", "BTCUSDT")
INTERVAL = os.getenv("INTERVAL", "1h")
LOOKBACK_DAYS = 365 * 2

# ------- Risk -------
RISK_PER_TRADE   = 0.01
MAX_DAILY_LOSS   = 0.03
MAX_POSITION_PCT = 0.20

# ------- Futures -------
LEVERAGE    = int(os.getenv("LEVERAGE", "3"))
MARGIN_TYPE = os.getenv("MARGIN_TYPE", "ISOLATED")

# SL/TP
ATR_SL_MULT = 1.5
ATR_TP_MULT = 3.0

# ------- Strategy -------
RSI_PERIOD      = 14
RSI_OVERSOLD    = 45
RSI_OVERBOUGHT  = 55
BB_PERIOD       = 20
BB_STD          = 2.0
ADX_PERIOD      = 14
ADX_THRESHOLD   = 25
ATR_PERIOD      = 14

# SHORT enable
ENABLE_SHORT = True

# ------- Execution -------
POLL_INTERVAL_SEC = int(os.getenv("POLL_INTERVAL_SEC", "300"))
