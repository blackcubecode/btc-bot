# 🤖 BTC Futures Trading Bot (Binance + Telegram)

Bot trading otomatis untuk **Binance Futures (USDⓈ-M)** yang terintegrasi dengan **Telegram Channel/Grup** untuk melaporkan status bot, posisi trading (Entry/Close), dan PnL secara real-time.

Bot ini dirancang menggunakan WebSocket untuk pemantauan harga, Rate Limiter untuk mengelola REST API, serta sistem Risk Management untuk membantu mengendalikan risiko trading.

> ⚠️ **Peringatan:** Bot menggunakan leverage pada pasar Futures. Selalu gunakan Binance Testnet sebelum melakukan trading dengan dana asli.

---

## ✨ Fitur Utama

### 🛡️ Anti-Ban Architecture
- WebSocket (`markPrice` dan `kline`) untuk mendapatkan data harga.
- REST API untuk eksekusi order dan pengecekan saldo.
- Rate Limiter untuk mengontrol frekuensi permintaan API.
- Exponential Backoff untuk menangani kegagalan koneksi dan pembatasan API.

### 📈 Dual Signal (LONG & SHORT)

Menggunakan kombinasi indikator teknikal:

- RSI (Relative Strength Index).
- Bollinger Bands.
- ADX (Average Directional Index).
- ATR (Average True Range).

Strategi dirancang untuk mendeteksi kondisi oversold dan overbought sebagai bagian dari analisis sinyal LONG dan SHORT.

### 🎯 Risk Management
- Perhitungan ukuran posisi (*Position Sizing*) berdasarkan persentase risiko per trade.
- Default risiko: 1% per trade.
- Daily Loss Limit untuk membatasi kerugian harian.
- Trailing Stop Loss dan Static Stop Loss.
- Take Profit berbasis ATR.
- Pengaturan leverage dan margin secara fleksibel.
- Dukungan konfigurasi batas budget.

> **Catatan:** Pastikan batas budget benar-benar diterapkan pada `RiskManager` dan order execution. Variabel konfigurasi saja tidak membatasi penggunaan dana.

### ⚡ Algo Order API

Mendukung penggunaan order Binance Futures untuk Stop Loss dan Take Profit:

- `STOP_MARKET`
- `TAKE_PROFIT_MARKET`

Implementasi menggunakan API Algo Order Binance apabila diwajibkan oleh endpoint atau jenis order yang digunakan.

Periksa dokumentasi Binance terbaru untuk memastikan endpoint sesuai dengan jenis kontrak dan order.

### 💰 PnL Kumulatif
- Menyimpan riwayat Profit/Loss secara permanen.
- Menghitung jumlah trade yang telah dilakukan.
- Menyimpan state bot pada `data/state.json`.
- Data tetap tersedia setelah bot di-restart selama file state tidak dihapus atau rusak.

### 📲 Telegram Notification

Notifikasi menggunakan format Hybrid (Emoji + Teks).

Informasi yang dikirim:

- Entry LONG dan SHORT.
- Close Position.
- Take Profit dan Stop Loss.
- Equity dan saldo.
- PnL per trade.
- PnL harian.
- Total PnL kumulatif.

### 🔄 Auto-Recovery
- Mendeteksi posisi yang masih terbuka saat bot dijalankan kembali.
- Membantu sinkronisasi kondisi bot dengan posisi Binance.
- Mengurangi risiko ketidaksesuaian status setelah restart.

---

## 📁 Struktur Proyek

```text
btc_bot/
├── core/
│   ├── binance_client.py
│   ├── websocket_manager.py
│   └── rate_limiter.py
│
├── data/
│   ├── state.json
│   └── parquet/
│
├── execution/
│   └── order_manager.py
│
├── models/
│   └── model_ml.py
│
├── monitoring/
│   ├── logger.py
│   ├── telegram.py
│   └── health.py
│
├── risk/
│   └── manager.py
│
├── strategy/
│   ├── indicators.py
│   └── signals.py
│
├── scripts/
│   └── healthcheck.sh
│
├── logs/
├── venv/
├── .env
├── .env.example
├── .gitignore
├── config.py
├── main.py
├── requirements.txt
└── README.md
```

---

# 🚀 Instalasi di VPS Linux

## 1. Persiapan Sistem

Pastikan VPS menggunakan Linux dan Python 3.10 atau versi yang kompatibel dengan dependensi proyek.

Install paket dasar:

```bash
sudo apt update

sudo apt install -y \
python3 \
python3-pip \
python3-venv \
git \
curl \
nano
```

## 2. Clone Repository

```bash
git clone https://github.com/blackcubecode/btc-bot.git

cd btc-bot
```

> Jika repository bersifat privat, pastikan akses GitHub sudah dikonfigurasi.

## 3. Membuat Virtual Environment

```bash
python3 -m venv venv

source venv/bin/activate
```

Upgrade pip:

```bash
pip install --upgrade pip
```

Install dependensi:

```bash
pip install -r requirements.txt
```

## 4. Konfigurasi Environment

Salin file konfigurasi contoh:

```bash
cp .env.example .env
```

Edit file:

```bash
nano .env
```

Isi konfigurasi:

```dotenv
# ==========================================
# TELEGRAM CONFIGURATION
# ==========================================

TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID=YOUR_TELEGRAM_CHAT_ID


# ==========================================
# BINANCE FUTURES CONFIGURATION
# ==========================================

BINANCE_FUTURES_API_KEY=YOUR_BINANCE_API_KEY
BINANCE_FUTURES_API_SECRET=YOUR_BINANCE_API_SECRET

# true = Testnet
# false = Live Trading

BINANCE_FUTURES_TESTNET=true


# ==========================================
# TRADING PARAMETERS
# ==========================================

SYMBOL=BTCUSDT
INTERVAL=1h

LEVERAGE=3
MARGIN_TYPE=ISOLATED

POLL_INTERVAL_SEC=300


# ==========================================
# RISK MANAGEMENT
# ==========================================

MAX_BUDGET_USDT=100
```

### Catatan keamanan

- Jangan pernah membagikan API Key atau API Secret.
- Jangan memasukkan file `.env` ke repository GitHub.
- Gunakan API Key khusus Futures dengan izin minimum.
- Nonaktifkan izin withdrawal pada API Key.
- Gunakan IP whitelist jika tersedia.
- Pastikan konfigurasi Testnet aktif sebelum pengujian.
- Jangan menyimpan API Key dalam source code.

## 5. Menjalankan Bot

Aktifkan virtual environment:

```bash
source venv/bin/activate
```

Jalankan:

```bash
python main.py
```

Bot akan mulai menjalankan strategi, memantau harga, dan mengirim notifikasi Telegram sesuai konfigurasi.

Untuk menghentikan bot manual:

```text
CTRL + C
```

---

# ⚙️ Menjalankan Bot sebagai Systemd Service

Systemd memungkinkan bot berjalan di background dan melakukan restart otomatis ketika proses mengalami kegagalan.

## 1. Buat Folder Log

```bash
mkdir -p /home/admin/bots/btc_bot/logs
```

Sesuaikan lokasi folder dengan direktori instalasi bot Anda.

## 2. Buat File Service

```bash
sudo nano /etc/systemd/system/btc_bot.service
```

Masukkan konfigurasi:

```ini
[Unit]
Description=BTC Futures Trading Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple

User=admin
Group=admin

WorkingDirectory=/home/admin/bots/btc_bot

Environment="PATH=/home/admin/bots/btc_bot/venv/bin:/usr/local/bin:/usr/bin:/bin"

ExecStart=/home/admin/bots/btc_bot/venv/bin/python /home/admin/bots/btc_bot/main.py

Restart=always
RestartSec=30

TimeoutStopSec=30

StandardOutput=append:/home/admin/bots/btc_bot/logs/systemd.log
StandardError=append:/home/admin/bots/btc_bot/logs/systemd.log

[Install]
WantedBy=multi-user.target
```

> Sesuaikan `User`, `Group`, dan seluruh path dengan lokasi instalasi sebenarnya.

## 3. Aktifkan Service

```bash
sudo systemctl daemon-reload

sudo systemctl enable btc_bot

sudo systemctl start btc_bot
```

## 4. Cek Status Bot

```bash
sudo systemctl status btc_bot
```

## 5. Melihat Log Real-Time

```bash
sudo journalctl -u btc_bot -f
```

## 6. Menghentikan Bot

```bash
sudo systemctl stop btc_bot
```

## 7. Restart Bot

```bash
sudo systemctl restart btc_bot
```

---

# 📊 Format Notifikasi Telegram

Bot menggunakan format Hybrid (Emoji + Teks) agar informasi trading mudah dibaca.

## Entry LONG / SHORT

Contoh notifikasi:

```text
🟢 LONG BTCUSDT

Qty: 0.038900 ($3000.00)

Entry: 79697.81
SL: 79249.60 (-0.56%)
TP: 80646.30 (+1.19%)

R:R = 1:2.00

━━━━━━━━━━━━━━

Equity: $4971.74
```

## Close Position (Take Profit / Stop Loss)

```text
🟢 CLOSE LONG BTCUSDT

Entry: 79697.81 -> Exit: 80646.30

Qty: 0.038900

━━━━━━━━━━━━━━

PnL Trade: +36.90 (+1.19%)
PnL Harian: +36.90 (+0.74%)

━━━━━━━━━━━━━━

Equity: $5008.64

Total PnL: +36.90 (1 trades)
```

> Nilai pada contoh notifikasi hanya ilustrasi dan bukan sinyal trading aktual.

---

# 🔧 Troubleshooting

## Bot tidak berjalan

Periksa status:

```bash
sudo systemctl status btc_bot
```

Periksa log:

```bash
sudo journalctl -u btc_bot -n 100
```

## Binance API Error

Periksa:

- API Key dan API Secret.
- Pengaturan Testnet atau Live.
- Izin API Futures.
- IP whitelist.
- Koneksi jaringan VPS.
- Rate limit dan pesan error Binance.

## Telegram tidak menerima notifikasi

Periksa:

- `TELEGRAM_BOT_TOKEN`.
- `TELEGRAM_CHAT_ID`.
- Bot sudah ditambahkan ke grup atau channel.
- Bot memiliki izin mengirim pesan.
- Koneksi Telegram dari VPS.

## Bot tidak mendeteksi posisi setelah restart

Periksa:

- File `data/state.json`.
- Posisi aktual pada Binance Futures.
- Log Auto-Recovery.
- Konsistensi konfigurasi simbol dan margin.

Jangan menghapus state atau membuka posisi baru sebelum memastikan status posisi Binance sudah benar.

---

# 🔥 Migrasi dari Testnet ke Binance Live (Real)

Bagian ini digunakan ketika bot sudah berhasil diuji pada Binance Testnet dan siap dipersiapkan untuk akun Live.

> ⚠️ **Trading Live menggunakan dana sungguhan. Kesalahan konfigurasi, API, leverage, atau ukuran posisi dapat menyebabkan kerugian finansial.**

## Langkah 0 — Persiapan Akun Binance Live

Sebelum mengubah kode di VPS, lakukan konfigurasi API pada website Binance.

### Membuat API Key

1. Login ke akun Binance.
2. Buka API Management.
3. Klik Create API.
4. Berikan nama API:

   `VPS_BTC_BOT`

5. Aktifkan izin Futures jika diperlukan oleh bot.
6. Jangan aktifkan izin Withdrawal.
7. Aktifkan IP whitelist.
8. Masukkan IP publik VPS.

### Mengetahui IP VPS

```bash
curl -4 ifconfig.me
```

Masukkan IP tersebut ke trusted IP Binance.

Pastikan VPS menggunakan IP publik yang stabil.

### Keamanan API Key

- API Key tidak boleh memiliki izin withdrawal.
- Jangan mengirim API Key melalui Telegram.
- Jangan mengunggah `.env` ke GitHub.
- Jangan memasukkan API Key ke README.
- Jika API Key bocor, segera cabut dan buat ulang.

### Memindahkan dana

Pindahkan dana ke Futures Wallet sesuai jenis kontrak yang digunakan.

Pastikan:

- Saldo tersedia.
- Aset margin sesuai.
- Simbol kontrak tersedia.
- Leverage dan margin mode sesuai konfigurasi.

**Catatan:** Jangan menganggap Binance memiliki fitur akun “Cent” atau bahwa BTCUSDC pasti tersedia pada akun Anda. Periksa kontrak Futures, aset margin, dan dukungan API secara langsung.

---

## Langkah 1 — Backup dan Update `.env`

Masuk ke direktori bot:

```bash
cd /home/admin/bots/btc_bot
```

Backup file:

```bash
cp .env .env.bak.$(date +%Y%m%d_%H%M%S)
```

Buka file:

```bash
nano .env
```

Gunakan konfigurasi berikut:

```dotenv
# ==========================================
# KONFIGURASI TELEGRAM
# ==========================================

TELEGRAM_BOT_TOKEN=MASUKKAN_TOKEN_TELEGRAM
TELEGRAM_CHAT_ID=MASUKKAN_CHAT_ID


# ==========================================
# BINANCE FUTURES API LIVE
# ==========================================

BINANCE_FUTURES_API_KEY=MASUKKAN_API_KEY_ASLI
BINANCE_FUTURES_API_SECRET=MASUKKAN_SECRET_KEY_ASLI

# FALSE = LIVE
# TRUE  = TESTNET

BINANCE_FUTURES_TESTNET=false


# ==========================================
# PARAMETER TRADING
# ==========================================

# Gunakan simbol yang benar-benar tersedia.
SYMBOL=BTCUSDC

INTERVAL=1h

LEVERAGE=3

MARGIN_TYPE=ISOLATED

POLL_INTERVAL_SEC=300


# ==========================================
# BATAS BUDGET
# ==========================================

MAX_BUDGET_USDT=100
```

Simpan dengan:

- `Ctrl + O`
- `Enter`
- `Ctrl + X`

### Penjelasan

| Parameter | Fungsi |
|---|---|
| `BINANCE_FUTURES_TESTNET` | `false` untuk Live |
| `SYMBOL` | Simbol kontrak Futures |
| `INTERVAL` | Timeframe strategi |
| `LEVERAGE` | Leverage |
| `MARGIN_TYPE` | Jenis margin |
| `POLL_INTERVAL_SEC` | Interval pemeriksaan |
| `MAX_BUDGET_USDT` | Target batas budget |

> **Penting:** `MAX_BUDGET_USDT=100` tidak otomatis membatasi penggunaan modal. Pastikan budget diterapkan pada sizing dan order execution sebelum Live.

---

## Langkah 2 — Update `config.py`

Backup:

```bash
cd /home/admin/bots/btc_bot

cp config.py config.py.bak.$(date +%Y%m%d_%H%M%S)
```

Buka:

```bash
nano config.py
```

Isi konfigurasi:

```python
"""Konfigurasi global bot — FUTURES LIVE/TESTNET."""

import os
from dotenv import load_dotenv

load_dotenv("/home/admin/bots/btc_bot/.env")


# ==========================================
# API
# ==========================================

FUTURES_API_KEY = os.getenv(
    "BINANCE_FUTURES_API_KEY"
)

FUTURES_API_SECRET = os.getenv(
    "BINANCE_FUTURES_API_SECRET"
)

FUTURES_TESTNET = (
    os.getenv(
        "BINANCE_FUTURES_TESTNET",
        "false"
    ).lower() == "true"
)


# ==========================================
# MARKET
# ==========================================

SYMBOL = os.getenv(
    "SYMBOL",
    "BTCUSDC"
)

INTERVAL = os.getenv(
    "INTERVAL",
    "1h"
)

LOOKBACK_DAYS = 365 * 2


# ==========================================
# RISK MANAGEMENT
# ==========================================

RISK_PER_TRADE = 0.01

MAX_DAILY_LOSS = 0.03

MAX_POSITION_PCT = 0.20

MAX_BUDGET_USDT = float(
    os.getenv(
        "MAX_BUDGET_USDT",
        "0"
    )
)


# ==========================================
# FUTURES
# ==========================================

LEVERAGE = int(
    os.getenv(
        "LEVERAGE",
        "3"
    )
)

MARGIN_TYPE = os.getenv(
    "MARGIN_TYPE",
    "ISOLATED"
)


# ==========================================
# SL / TP
# ==========================================

ATR_SL_MULT = 1.5

ATR_TP_MULT = 3.0


# ==========================================
# STRATEGY
# ==========================================

RSI_PERIOD = 14

RSI_OVERSOLD = 45

RSI_OVERBOUGHT = 55

BB_PERIOD = 20

BB_STD = 2.0

ADX_PERIOD = 14

ADX_THRESHOLD = 25

ATR_PERIOD = 14


# ==========================================
# SHORT
# ==========================================

ENABLE_SHORT = True


# ==========================================
# EXECUTION
# ==========================================

POLL_INTERVAL_SEC = int(
    os.getenv(
        "POLL_INTERVAL_SEC",
        "300"
    )
)
```

---

## Langkah 3 — Update dan Audit `main.py`

Backup file:

```bash
cd /home/admin/bots/btc_bot

cp main.py main.py.bak.$(date +%Y%m%d_%H%M%S)
```

Buka:

```bash
nano main.py
```

Gunakan `main.py` versi terbaru yang telah diuji pada Testnet.

Pastikan kode mempertahankan:

- WebSocket manager.
- REST client.
- LONG dan SHORT.
- RiskManager.
- Telegram notification.
- Monitoring kesehatan WebSocket.
- State PnL kumulatif.
- Recovery posisi.
- Daily loss limit.
- SL dan TP.
- Shutdown handling.

### Pemeriksaan wajib

Periksa file:

```text
core/binance_client.py
core/websocket_manager.py
risk/manager.py
execution/order_manager.py
monitoring/telegram.py
```

Pastikan:

1. `get_equity()` membaca saldo yang benar.
2. `get_position()` membaca posisi yang benar.
3. `setup_symbol()` menggunakan kontrak yang tersedia.
4. `open_long()` dan `open_short()` mengirim order sesuai aturan Binance.
5. `close_position()` menutup posisi yang dimaksud.
6. Quantity mengikuti step size dan minimum quantity.
7. SL/TP benar-benar terpasang di Binance.
8. API client menggunakan endpoint Live ketika Testnet dinonaktifkan.

---

## Langkah 4 — Validasi Budget dan Risk Management

**Ini adalah pemeriksaan paling penting sebelum trading Live.**

Pada kode `main.py`, ukuran posisi dihitung menggunakan:

```python
qty = risk.position_size(
    row["close"],
    row["atr"]
)
```

Jika `RiskManager` menggunakan seluruh equity, maka:

```text
Saldo Futures       : $500
MAX_BUDGET_USDT    : $100
```

bot berpotensi menghitung posisi berdasarkan $500, bukan $100.

### Yang harus diperiksa

Pastikan `RiskManager`:

- Membatasi equity yang digunakan untuk sizing.
- Memeriksa budget sebelum order.
- Menghitung risiko berdasarkan budget yang diizinkan.
- Menghentikan pembukaan posisi jika batas terlampaui.

**Jangan menganggap budget aktif hanya karena muncul pada pesan Telegram.**

Budget juga bukan jaminan batas kerugian maksimum. Leverage, slippage, funding, biaya, dan likuidasi tetap dapat menyebabkan kerugian.

---

## Langkah 5 — Validasi Python

Aktifkan virtual environment:

```bash
cd /home/admin/bots/btc_bot

source venv/bin/activate
```

Periksa syntax:

```bash
python -c "import ast; [ast.parse(open(f).read()) for f in ['config.py', 'main.py']]; print('syntax OK')"
```

Output:

```text
syntax OK
```

Periksa dependency:

```bash
python -m pip check
```

Periksa konfigurasi tanpa menampilkan API Key:

```bash
python -c "import config; print('TESTNET:', config.FUTURES_TESTNET); print('SYMBOL:', config.SYMBOL); print('LEVERAGE:', config.LEVERAGE); print('BUDGET:', config.MAX_BUDGET_USDT)"
```

Pastikan:

```text
TESTNET: False
SYMBOL: BTCUSDC
LEVERAGE: 3
BUDGET: 100.0
```

Output di atas hanya contoh.

Jangan mencetak API Key atau Secret Key ke terminal maupun log.

---

## Langkah 6 — Restart Bot Live

Setelah pemeriksaan selesai:

```bash
sudo systemctl restart btc_bot
```

Tunggu:

```bash
sleep 15
```

Periksa status:

```bash
sudo systemctl status btc_bot --no-pager
```

Periksa log:

```bash
tail -15 /home/admin/bots/btc_bot/logs/main.log
```

Pantau secara langsung:

```bash
tail -f /home/admin/bots/btc_bot/logs/main.log
```

Untuk keluar dari pemantauan:

```text
Ctrl + C
```

Perintah tersebut tidak otomatis menghentikan service bot.

---

## Langkah 7 — Verifikasi Telegram

Jika berhasil, pesan startup akan menampilkan:

```text
🤖 Bot start

Mode: LIVE 🔥
Symbol: BTCUSDC
Interval: 1h
Leverage: 3x
Budget: $100.00

Total PnL: +0.00 (0 trades)
```

Periksa:

- Mode LIVE.
- Simbol sesuai kontrak.
- Leverage sesuai.
- Budget sesuai.
- Saldo sesuai akun.
- Posisi existing terdeteksi.
- Tidak ada error API.

> Pesan LIVE hanya menunjukkan konfigurasi bot. Pesan tersebut tidak membuktikan bahwa seluruh proteksi trading telah benar.

---

## Langkah 8 — Perintah Mengelola Bot

### Melihat status

```bash
sudo systemctl status btc_bot
```

### Menghentikan bot

```bash
sudo systemctl stop btc_bot
```

### Menyalakan bot

```bash
sudo systemctl start btc_bot
```

### Restart bot

```bash
sudo systemctl restart btc_bot
```

### Melihat log

```bash
tail -f /home/admin/bots/btc_bot/logs/main.log
```

### Memastikan proses berjalan

```bash
pgrep -af "python.*main.py"
```

---

## Langkah 9 — Checklist Sebelum Trading Live

- [ ] API Key Live sudah dibuat.
- [ ] IP VPS sudah masuk whitelist.
- [ ] Withdrawal tidak diaktifkan.
- [ ] API Key tidak tersimpan di GitHub.
- [ ] Saldo Futures tersedia.
- [ ] Simbol BTCUSDC/BTCUSDT telah diverifikasi.
- [ ] Aset margin sesuai.
- [ ] Leverage diperiksa.
- [ ] Margin mode diperiksa.
- [ ] SL/TP sudah diuji.
- [ ] Budget benar-benar diterapkan.
- [ ] RiskManager sudah diperiksa.
- [ ] Minimum quantity dan notional sudah diperiksa.
- [ ] Daily loss limit sudah diuji.
- [ ] Posisi terbuka sudah diperiksa.
- [ ] Bot sudah diuji pada Testnet.
- [ ] Telegram notification berfungsi.
- [ ] Emergency stop sudah dipahami.

---

## Langkah 10 — Emergency Stop

Jika bot mengalami masalah:

```bash
sudo systemctl stop btc_bot
```

Kemudian periksa posisi langsung di Binance Futures.

**Menghentikan bot tidak otomatis menutup posisi Futures yang sudah terbuka.**

Setelah bot berhenti:

1. Buka Binance Futures.
2. Periksa posisi aktif.
3. Pastikan SL/TP masih terpasang.
4. Tutup posisi secara manual jika diperlukan.
5. Periksa order terbuka.
6. Jangan restart bot sebelum penyebab masalah diketahui.

---

# ⚠️ Disclaimer

Trading cryptocurrency, khususnya Binance Futures dengan leverage, memiliki risiko finansial yang sangat tinggi.

- Leverage memperbesar keuntungan sekaligus kerugian.
- Stop Loss tidak menjamin harga eksekusi sesuai harga yang ditentukan.
- Gangguan jaringan, slippage, likuidasi, dan kesalahan API dapat menyebabkan kerugian.
- Hasil backtest atau Testnet tidak menjamin performa Live Trading.
- Selalu uji bot menggunakan Testnet sebelum menggunakan dana asli.
- Gunakan dana yang siap Anda tanggung risikonya.

**Developer tidak bertanggung jawab atas kerugian finansial, kehilangan aset, atau kerusakan yang timbul akibat penggunaan bot ini.**

---

# 🧊 Black Cube Code

**BTC Futures Trading Bot — Binance + Telegram**

Developed by Black Cube Code.

Repository:

[https://github.com/blackcubecode/btc-bot](https://github.com/blackcubecode/btc-bot)

---

## 💖 Support dan Donasi

Jika proyek ini bermanfaat, dukung pengembangan Black Cube Code melalui donasi sukarela.

<p align="center">
  <img
    src="qris-donasi.jpg"
    width="300"
    alt="QRIS Donasi Black Cube Code"
  >
</p>

<p align="center">
  <em>Terima kasih atas dukungan Anda untuk pengembangan software independen.</em>
</p>

---

**Black Cube Code — BTC Futures Trading Bot**
