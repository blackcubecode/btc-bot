# 🤖 BTC Futures Trading Bot (Binance + Telegram)

Bot trading otomatis untuk **Binance Futures (USDⓈ-M)** yang terintegrasi dengan **Telegram Channel/Grup** untuk melaporkan status bot, posisi trading (Entry/Close), dan PnL secara real-time.

Bot ini dirancang menggunakan WebSocket untuk pemantauan harga, Rate Limiter untuk mengelola REST API, serta sistem Risk Management untuk membantu mengendalikan risiko trading.

> ⚠️ **Peringatan:** Bot ini menggunakan leverage pada pasar Futures. Selalu gunakan Binance Testnet sebelum melakukan trading dengan dana asli.

---

## ✨ Fitur Utama

### 🛡️ Anti-Ban Architecture
- Menggunakan WebSocket (`markPrice` dan `kline`) untuk mendapatkan data harga real-time.
- REST API digunakan untuk kebutuhan eksekusi order dan pengecekan saldo.
- Rate Limiter untuk mengontrol frekuensi permintaan API.
- Exponential Backoff untuk menangani kegagalan koneksi dan pembatasan API.

### 📈 Dual Signal (LONG & SHORT)
Menggunakan kombinasi indikator teknikal:
- RSI (Relative Strength Index).
- Bollinger Bands.
- ADX (Average Directional Index).

Strategi dirancang untuk mendeteksi kondisi oversold dan overbought sebagai bagian dari analisis sinyal LONG dan SHORT.

### 🎯 Risk Management
- Perhitungan ukuran posisi (*Position Sizing*) berdasarkan persentase risiko per trade.
- Default risiko: 1% per trade.
- Daily Loss Limit untuk membatasi kerugian harian.
- Trailing Stop Loss dan Static Stop Loss.
- Take Profit berbasis ATR (Average True Range).
- Pengaturan leverage dan margin secara fleksibel.

### ⚡ Algo Order API
Mendukung penggunaan order Binance Futures untuk Stop Loss dan Take Profit:

- `STOP_MARKET`
- `TAKE_PROFIT_MARKET`

Implementasi menggunakan API Algo Order Binance untuk menghindari error `-4120` pada endpoint order yang tidak sesuai.

### 💰 PnL Kumulatif
- Menyimpan riwayat Profit/Loss secara permanen.
- Menghitung jumlah trade yang telah dilakukan.
- Menyimpan state bot pada `data/state.json`.
- Data tetap tersedia setelah bot di-restart, selama file state tidak dihapus atau rusak.

### 📲 Telegram Notification
Notifikasi menggunakan format Hybrid (Emoji + Teks) yang mudah dibaca.

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
- Membantu sinkronisasi kondisi bot dengan posisi yang ada di Binance.
- Mengurangi risiko ketidaksesuaian status setelah restart.

---

## 📁 Struktur Proyek

```text
btc_bot/
├── core/
│   ├── Binance Client
│   ├── WebSocket Manager
│   └── Rate Limiter
│
├── data/
│   ├── state.json
│   └── parquet/
│
├── execution/
│   └── Order Manager (Market, SL/TP, Close)
│
├── models/
│   └── Model ML (Opsional)
│
├── monitoring/
│   ├── Logger
│   ├── Telegram Alert
│   └── Health Check
│
├── risk/
│   └── Risk Manager (Sizing, SL/TP)
│
├── strategy/
│   ├── RSI
│   ├── Bollinger Bands
│   ├── ATR
│   └── LONG/SHORT Signal
│
├── scripts/
│   └── healthcheck.sh
│
├── .env
├── .env.example
├── .gitignore
├── config.py
├── main.py
├── requirements.txt
└── README.md
```

---

## 🚀 Instalasi di VPS Linux

### 1. Persiapan Sistem

Pastikan VPS menggunakan Linux dan Python 3.10 atau versi yang kompatibel dengan dependensi proyek.

Install paket dasar:

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git
```

### 2. Clone Repository

```bash
git clone https://github.com/blackcubecode/btc-bot.git

cd btc-bot
```

### 3. Membuat Virtual Environment

```bash
python3 -m venv venv

source venv/bin/activate
```

Upgrade pip:

```bash
pip install --upgrade pip
```

Install seluruh dependensi:

```bash
pip install -r requirements.txt
```

### 4. Konfigurasi Environment

Salin file konfigurasi contoh:

```bash
cp .env.example .env
```

Edit file:

```bash
nano .env
```

Isi konfigurasi sesuai akun Binance dan Telegram Anda.

```env
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
```

**Catatan keamanan:**
- Jangan pernah membagikan API Key atau API Secret.
- Jangan memasukkan file `.env` ke repository GitHub.
- Gunakan API Key khusus Futures dengan izin minimum.
- Nonaktifkan izin withdrawal pada API Key.
- Gunakan IP whitelist jika tersedia.
- Pastikan konfigurasi Testnet aktif sebelum pengujian.

### 5. Menjalankan Bot

Aktifkan virtual environment:

```bash
source venv/bin/activate
```

Jalankan:

```bash
python main.py
```

Bot akan mulai menjalankan strategi, memantau harga, dan mengirim notifikasi Telegram sesuai konfigurasi.

Untuk menghentikan bot manual, tekan:

```text
CTRL + C
```

---

## ⚙️ Menjalankan Bot sebagai Systemd Service

Systemd memungkinkan bot berjalan di background dan melakukan restart otomatis ketika proses mengalami kegagalan.

### 1. Buat Folder Log

```bash
mkdir -p /home/admin/bots/btc_bot/logs
```

Sesuaikan lokasi folder dengan direktori instalasi bot Anda.

### 2. Buat File Service

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

### 3. Aktifkan Service

```bash
sudo systemctl daemon-reload

sudo systemctl enable btc_bot

sudo systemctl start btc_bot
```

### 4. Cek Status Bot

```bash
sudo systemctl status btc_bot
```

### 5. Melihat Log Real-Time

```bash
sudo journalctl -u btc_bot -f
```

### 6. Menghentikan Bot

```bash
sudo systemctl stop btc_bot
```

### 7. Restart Bot

```bash
sudo systemctl restart btc_bot
```

---

## 📊 Format Notifikasi Telegram

Bot menggunakan format Hybrid (Emoji + Teks) agar informasi trading mudah dibaca.

### Entry LONG / SHORT

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

### Close Position (Take Profit / Stop Loss)

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

## 🔧 Troubleshooting

### Bot tidak berjalan

Periksa status:

```bash
sudo systemctl status btc_bot
```

Periksa log:

```bash
sudo journalctl -u btc_bot -n 100
```

### Binance API Error

Periksa:
- API Key dan API Secret.
- Pengaturan Testnet atau Live.
- Izin API Futures.
- IP whitelist.
- Koneksi jaringan VPS.
- Rate limit dan pesan error Binance.

### Telegram tidak menerima notifikasi

Periksa:
- `TELEGRAM_BOT_TOKEN`.
- `TELEGRAM_CHAT_ID`.
- Bot sudah ditambahkan ke grup atau channel.
- Bot memiliki izin mengirim pesan.
- Koneksi Telegram dari VPS.

### Bot tidak mendeteksi posisi setelah restart

Periksa:
- File `data/state.json`.
- Posisi aktual pada Binance Futures.
- Log Auto-Recovery.
- Konsistensi konfigurasi simbol dan margin.

Jangan menghapus state atau membuka posisi baru sebelum memastikan status posisi Binance sudah benar.

---

## ⚠️ Disclaimer

Trading cryptocurrency, khususnya Binance Futures dengan leverage, memiliki risiko finansial yang sangat tinggi.

- Leverage dapat memperbesar keuntungan sekaligus kerugian.
- Stop Loss tidak menjamin harga eksekusi sesuai harga yang ditentukan.
- Gangguan jaringan, slippage, likuidasi, dan kesalahan API dapat menyebabkan kerugian.
- Hasil backtest atau Testnet tidak menjamin performa Live Trading.
- Selalu uji bot menggunakan Testnet sebelum menggunakan dana asli.
- Gunakan dana yang siap Anda tanggung risikonya.

**Developer tidak bertanggung jawab atas kerugian finansial, kehilangan aset, atau kerusakan yang timbul akibat penggunaan bot ini.**

---

## 🧊 Black Cube Code

**BTC Futures Trading Bot — Binance + Telegram**

Developed by Black Cube Code.

Repository: [https://github.com/blackcubecode/btc-bot](https://github.com/blackcubecode/btc-bot)
## 💖 Support dan Donasi

Jika proyek ini bermanfaat, dukung pengembangan Black Cube ScannerFX melalui donasi sukarela.

<p align="center">
  <img src="qris-donasi.jpg" width="300" alt="QRIS Donasi Black Cube Code">
</p>

<p align="center">
  <em>Terima kasih atas dukungan Anda untuk pengembangan software independen.</em>
</p>

---
