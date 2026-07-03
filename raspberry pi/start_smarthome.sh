#!/bin/bash
# ==========================================
#  START SMART HOME - SEMUA SEKALIGUS
#  Jalankan: bash start_smarthome.sh
# ==========================================

PROJECT_DIR=~/smart_home
WEB_PORT=8080
LOG_DIR=$PROJECT_DIR/logs

# Buat folder log
mkdir -p $LOG_DIR

echo ""
echo "================================================"
echo "  🏠 SMART HOME - STARTING ALL SERVICES"
echo "================================================"
echo ""

# ── 1. Deteksi Port Arduino ──
echo "🔍 Mencari port Arduino..."
ARDUINO_PORT=""

for port in /dev/ttyUSB0 /dev/ttyUSB1 /dev/ttyACM0 /dev/ttyACM1; do
    if [ -e "$port" ]; then
        ARDUINO_PORT=$port
        echo "✅ Arduino ditemukan di: $ARDUINO_PORT"
        break
    fi
done

if [ -z "$ARDUINO_PORT" ]; then
    echo "⚠️  Arduino tidak ditemukan! Berjalan dalam mode simulasi."
    ARDUINO_PORT="/dev/ttyUSB0"
fi

# Update port di file Python secara otomatis
sed -i "s|SERIAL_PORT = '.*'|SERIAL_PORT = '$ARDUINO_PORT'|g" \
    $PROJECT_DIR/main_assistant_raspi.py
echo "📝 Serial port diupdate ke: $ARDUINO_PORT"

echo ""

# ── 2. Jalankan Web Server ──
echo "🌐 [1/3] Menjalankan Web Server di port $WEB_PORT..."
cd $PROJECT_DIR
python3 -m http.server $WEB_PORT \
    > $LOG_DIR/webserver.log 2>&1 &
WEB_PID=$!
echo "✅ Web Server PID: $WEB_PID"
echo "   Akses lokal: http://localhost:$WEB_PORT"

sleep 1

# ── 3. Jalankan ngrok ──
echo ""
echo "🌍 [2/3] Menjalankan ngrok tunnel..."
ngrok http $WEB_PORT \
    > $LOG_DIR/ngrok.log 2>&1 &
NGROK_PID=$!
echo "✅ ngrok PID: $NGROK_PID"

# Tunggu ngrok siap (maks 10 detik)
echo "   Menunggu ngrok siap..."
sleep 5

# Ambil URL publik ngrok
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels 2>/dev/null \
    | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    url = data['tunnels'][0]['public_url']
    print(url)
except:
    print('URL_BELUM_TERSEDIA')
")

echo ""
echo "================================================"
echo "  📱 URL UNTUK HANDPHONE:"
echo "  $NGROK_URL"
echo "================================================"
echo ""

# Simpan URL ke file agar mudah dibaca
echo "$NGROK_URL" > $PROJECT_DIR/ngrok_url.txt
echo "💾 URL disimpan di: $PROJECT_DIR/ngrok_url.txt"

# ── 4. Jalankan Voice Assistant ──
echo ""
echo "🤖 [3/3] Menjalankan Voice Assistant (AI)..."
cd $PROJECT_DIR
python3 main_assistant_raspi.py \
    > $LOG_DIR/assistant.log 2>&1 &
ASSISTANT_PID=$!
echo "✅ Assistant PID: $ASSISTANT_PID"

# Simpan semua PID untuk keperluan stop
echo "$WEB_PID $NGROK_PID $ASSISTANT_PID" > $PROJECT_DIR/running_pids.txt

echo ""
echo "================================================"
echo "  ✅ SEMUA SERVICE BERJALAN!"
echo "================================================"
echo ""
echo "📱 Buka di HP: $NGROK_URL"
echo "🖥️  Buka lokal: http://localhost:$WEB_PORT"
echo ""
echo "📋 Log files:"
echo "   Web Server : $LOG_DIR/webserver.log"
echo "   ngrok      : $LOG_DIR/ngrok.log"
echo "   Assistant  : $LOG_DIR/assistant.log"
echo ""
echo "🛑 Untuk menghentikan semua: bash stop_smarthome.sh"
echo ""

# Tampilkan log assistant secara live
echo "─── Live Log Assistant ───"
tail -f $LOG_DIR/assistant.log
