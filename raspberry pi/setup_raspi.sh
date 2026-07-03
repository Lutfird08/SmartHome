#!/bin/bash
# ==========================================
#  SETUP OTOMATIS - SMART HOME RASPBERRY PI
#  Jalankan: bash setup_raspi.sh
# ==========================================

echo ""
echo "================================================"
echo "  🏠 SMART HOME - SETUP RASPBERRY PI"
echo "================================================"
echo ""

# ── Update sistem ──
echo "📦 [1/6] Update sistem..."
sudo apt-get update -y
sudo apt-get upgrade -y

# ── Install Python & pip ──
echo ""
echo "🐍 [2/6] Install Python dependencies..."
sudo apt-get install -y python3-pip python3-dev

# ── Install library Python ──
echo ""
echo "📚 [3/6] Install library Python..."
pip3 install --break-system-packages \
    tensorflow \
    keras \
    nltk \
    numpy \
    pyserial \
    paho-mqtt \
    gtts \
    pygame \
    SpeechRecognition \
    pyaudio

# ── Download NLTK data ──
echo ""
echo "📖 [4/6] Download NLTK data..."
python3 -c "
import nltk
nltk.download('punkt')
nltk.download('wordnet')
nltk.download('omw-1.4')
print('✅ NLTK data berhasil didownload')
"

# ── Install & Setup ngrok ──
echo ""
echo "🌐 [5/6] Install ngrok..."
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt-get update -y
sudo apt-get install -y ngrok

echo ""
echo "⚠️  PENTING: Daftarkan akun ngrok di https://ngrok.com"
echo "   Lalu masukkan authtoken kamu:"
echo "   ngrok config add-authtoken YOUR_TOKEN_DISINI"
echo ""

# ── Setup folder proyek ──
echo ""
echo "📁 [6/6] Setup folder proyek..."
mkdir -p ~/smart_home
echo "✅ Folder ~/smart_home dibuat"

echo ""
echo "================================================"
echo "  ✅ SETUP SELESAI!"
echo "================================================"
echo ""
echo "Langkah selanjutnya:"
echo "1. Pindahkan semua file proyek ke folder ~/smart_home"
echo "2. Jalankan: bash start_smarthome.sh"
echo ""
