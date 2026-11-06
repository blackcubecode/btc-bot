#!/bin/bash
# Health check: restart btc_bot kalau log tidak update > 10 menit
# (POLL_INTERVAL_SEC=300 + buffer 5 min)
LOG="/home/admin/bots/btc_bot/logs/main.log"

if [ ! -f "$LOG" ]; then
    echo "[$(date)] Log not found � skip"
    exit 0
fi

LAST_MTIME=$(stat -c %Y "$LOG")
NOW=$(date +%s)
AGE=$((NOW - LAST_MTIME))

if [ $AGE -gt 600 ]; then
    echo "[$(date)] ?? Log stale ${AGE}s (>600s) � restarting btc_bot"
    sudo systemctl restart btc_bot
else
    echo "[$(date)] ? Log fresh (${AGE}s ago)"
fi
