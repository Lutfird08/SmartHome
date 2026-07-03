#!/bin/bash
# ==========================================
#  STOP SMART HOME - HENTIKAN SEMUA SERVICE
#  Jalankan: bash stop_smarthome.sh
# ==========================================

PROJECT_DIR=~/smart_home

echo ""
echo "🛑 Menghentikan semua service Smart Home..."

if [ -f "$PROJECT_DIR/running_pids.txt" ]; then
    PIDS=$(cat $PROJECT_DIR/running_pids.txt)
    for PID in $PIDS; do
        if kill -0 $PID 2>/dev/null; then
            kill $PID
            echo "✅ PID $PID dihentikan"
        fi
    done
    rm $PROJECT_DIR/running_pids.txt
else
    # Fallback: kill by name
    pkill -f "http.server"
    pkill -f "ngrok"
    pkill -f "main_assistant_raspi.py"
    echo "✅ Semua proses dihentikan"
fi

echo ""
echo "✅ Smart Home dimatikan."
echo ""
