# ==========================================
#  ASISTEN SUARA PINTAR - RASPBERRY PI
#  Fix: MQTT Topic & Format Perintah Arduino
# ==========================================

import warnings
warnings.filterwarnings("ignore")

import nltk
from nltk.stem import WordNetLemmatizer
import json
import pickle
import serial
import webbrowser
import numpy as np
import random
from keras.models import load_model
import speech_recognition as sr
from gtts import gTTS
from io import BytesIO
import pygame
import datetime
import locale
import time
import paho.mqtt.client as mqtt

# ==========================================
# 1. KONFIGURASI MQTT
#    - Semua topic sudah diseragamkan
#      dengan web (home.js)
# ==========================================
MQTT_BROKER  = "broker.emqx.io"
MQTT_PORT    = 1883

# TOPIC — sama persis dengan home.js
TOPIC_CONTROL     = "smart_home/control"       # Web kirim perintah ke Arduino
TOPIC_STATUS      = "smart_home/status"        # Status perangkat → Web
TOPIC_SENSOR      = "smart_home/sensor"        # Data sensor → Web
TOPIC_VOICE_INPUT = "smart_home/voice_input"   # Web kirim teks ke AI
TOPIC_VOICE_REPLY = "smart_home/voice_reply"   # AI balas teks ke Web

# Antrian perintah dari web
web_command_queue = []

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ MQTT Terhubung ke broker!")
        client.subscribe(TOPIC_VOICE_INPUT)
        print(f"👂 Mendengarkan perintah web di: {TOPIC_VOICE_INPUT}")
    else:
        print(f"❌ Gagal konek MQTT, kode: {rc}")

def on_message(client, userdata, msg):
    text = msg.payload.decode("utf-8").strip()
    print(f"📩 Perintah dari Web: [{text}]")
    if text:
        web_command_queue.append(text)

client_mqtt = mqtt.Client(client_id="raspi_assistant_" + str(random.randint(1000,9999)))
client_mqtt.on_connect = on_connect
client_mqtt.on_message = on_message

try:
    client_mqtt.connect(MQTT_BROKER, MQTT_PORT, 60)
    client_mqtt.loop_start()
    print("✅ MQTT client dimulai")
except Exception as e:
    print(f"❌ Gagal konek MQTT: {e}")

# ==========================================
# 2. KONFIGURASI SERIAL ARDUINO
#    - Di Raspberry Pi, port Arduino biasanya
#      /dev/ttyUSB0 atau /dev/ttyACM0
#    - Cek dengan perintah: ls /dev/tty*
# ==========================================
SERIAL_PORT = '/dev/ttyUSB0'  # Ganti jika perlu: /dev/ttyACM0
BAUD_RATE   = 115200

try:
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)
    print(f"✅ Arduino terhubung di {SERIAL_PORT}")
except Exception as e:
    print(f"❌ Gagal konek Arduino: {e}")
    print("⚠️  Berjalan dalam MODE SIMULASI (tanpa hardware)")
    arduino = None

# ==========================================
# 3. LOAD MODEL AI
# ==========================================
try:
    lemmatizer = WordNetLemmatizer()
    model      = load_model('model.h5')
    intents    = json.loads(open("intents.json").read())
    words      = pickle.load(open('words.pkl', 'rb'))
    classes    = pickle.load(open('classes.pkl', 'rb'))
    print("✅ Model AI berhasil dimuat!")
except Exception as e:
    print(f"❌ Gagal muat Model AI: {e}")
    exit()

# ==========================================
# 4. MAPPING PERINTAH AI → FORMAT ARDUINO
#
#    PERBAIKAN UTAMA:
#    Sebelum (lama)  →  Sesudah (sesuai .ino)
#    "lampu1_hidup"  →  "ON 0"
#    "lampu1_mati"   →  "OFF 0"
#    "kipas_hidup"   →  "KIPASON 50"
#    dst.
# ==========================================
arduino_commands = {
    # LAMPU — index sesuai buttonNames di Arduino
    'lampu1_hidup':      'ON 0',           # Lampu Utama
    'lampu1_mati':       'OFF 0',
    'lampu2_hidup':      'ON 1',           # Lampu Kamar
    'lampu2_mati':       'OFF 1',
    'lampu3_hidup':      'ON 2',           # Lampu Tamu
    'lampu3_mati':       'OFF 2',

    # SEMUA LAMPU — kirim satu per satu dengan jeda
    'lampusemua_hidup':  'ALL_LAMPU_ON',   # Ditangani khusus di send_to_arduino()
    'lampusemua_mati':   'ALL_LAMPU_OFF',

    # TERMINAL / COLOKAN
    'terminal_hidup':    'ON 3',
    'terminal_mati':     'OFF 3',

    # KIPAS — KIPASON {speed}, speed 1-100
    'kipas_hidup':       'KIPASON 50',
    'kipas_mati':        'KIPASOFF',
    'kipas_naik':        'KIPASON 100',    # Speed naik ke 100%
    'kipas_turun':       'KIPASON 33',     # Speed turun ke 33%

    # POMPA PENYIRAM
    'pompa_hidup':       'ON 7',
    'pompa_mati':        'OFF 7',

    # SALURAN AIR (SOLENOID VALVE)
    'kran_hidup':        'ON 8',
    'kran_mati':         'OFF 8',

    # PINTU (SOLENOID DOOR — auto off 5 detik di Arduino)
    'kunci_mati':        'ON 9',           # Buka pintu
    'kunci_hidup':       'OFF 9',          # Kunci pintu (jarang dipakai manual)

    # TIRAI — pakai L298N motor
    'tirai_hidup':       'TIRAITUTUP 45',  # Tutup tirai
    'tirai_mati':        'TIRAIBUKA 45',   # Buka tirai

    # AC — pakai IR relay (pulse)
    'ac_hidup':          'AC_POWER',
    'ac_mati':           'AC_POWER',       # Toggle, sama-sama AC_POWER
    'ac_naik':           'AC_UP',
    'ac_turun':          'AC_DOWN',

    # OTOMATIS
    'otopompa_hidup':    'ON 10',
    'otopompa_mati':     'OFF 10',
    'otolampu_hidup':    'ON 11',
    'otolampu_mati':     'OFF 11',

    # PERGI — matikan semua
    'pergi':             'ALL_OFF',        # Ditangani khusus
}

# ==========================================
# 5. FUNGSI NLP
# ==========================================
def clean_up_sentence(sentence):
    sentence_words = nltk.word_tokenize(sentence)
    sentence_words = [lemmatizer.lemmatize(w.lower()) for w in sentence_words]
    return sentence_words

def bow(sentence, words):
    sentence_words = clean_up_sentence(sentence)
    bag = [0] * len(words)
    for s in sentence_words:
        for i, w in enumerate(words):
            if w == s:
                bag[i] = 1
    return np.array(bag)

def predict_class(sentence):
    p       = bow(sentence, words)
    res     = model.predict(np.array([p]), verbose=0)[0]
    results = [[i, r] for i, r in enumerate(res) if r > 0.25]
    results.sort(key=lambda x: x[1], reverse=True)
    return [{"intent": classes[r[0]], "probability": str(r[1])} for r in results]

def get_response(ints):
    if not ints:
        return "Maaf, saya tidak mengerti.", "unknown"
    tag = ints[0]['intent']
    for i in intents['intents']:
        if i['tag'] == tag:
            return random.choice(i['responses']), tag
    return "Maaf, saya tidak mengerti.", "unknown"

def chatbot_response(text):
    ints = predict_class(text)
    return get_response(ints)

# ==========================================
# 6. FUNGSI SUARA (TEXT TO SPEECH)
# ==========================================
def speak(text):
    try:
        pygame.mixer.init()
        tts    = gTTS(text=text, lang="id", slow=False)
        mp3_fp = BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        pygame.mixer.music.load(mp3_fp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except Exception as e:
        print(f"⚠️ Error TTS: {e}")

# ==========================================
# 7. FUNGSI KIRIM PERINTAH KE ARDUINO
#    + Publish status ke Web via MQTT
# ==========================================

# Peta status untuk dikirim ke Web setelah eksekusi
status_map = {
    'ON 0':        'lampu_utama:ON',
    'OFF 0':       'lampu_utama:OFF',
    'ON 1':        'lampu_kamar:ON',
    'OFF 1':       'lampu_kamar:OFF',
    'ON 2':        'lampu_tamu:ON',
    'OFF 2':       'lampu_tamu:OFF',
    'ON 3':        'colokan_terminal:ON',
    'OFF 3':       'colokan_terminal:OFF',
    'KIPASON 50':  'kipas:ON',
    'KIPASON 33':  'kipas:ON',
    'KIPASON 100': 'kipas:ON',
    'KIPASOFF':    'kipas:OFF',
    'ON 7':        'pompa_penyiram:ON',
    'OFF 7':       'pompa_penyiram:OFF',
    'ON 8':        'solenoid_valve:ON',
    'OFF 8':       'solenoid_valve:OFF',
    'ON 9':        'solenoid_door:ON',
    'OFF 9':       'solenoid_door:OFF',
    'TIRAIBUKA 45':  'tirai:BUKA',
    'TIRAITUTUP 45': 'tirai:TUTUP',
    'AC_POWER':    'ac_power:PULSE',
    'AC_UP':       'ac_up:PULSE',
    'AC_DOWN':     'ac_down:PULSE',
    'ON 10':       'otomatis_pompa:ON',
    'OFF 10':      'otomatis_pompa:OFF',
    'ON 11':       'otomatis_lampu:ON',
    'OFF 11':      'otomatis_lampu:OFF',
}

def kirim_serial(command):
    """Kirim satu perintah ke Arduino via Serial."""
    if arduino and arduino.is_open:
        arduino.write((command + '\n').encode())
        print(f"📤 → Arduino: {command}")
        time.sleep(0.15)
    else:
        print(f"🔵 [SIMULASI] Perintah: {command}")

def send_to_arduino(tag, command):
    """
    Eksekusi perintah ke Arduino dan
    publish status ke MQTT agar Web ikut update.
    """

    # --- Kasus Khusus: SEMUA LAMPU ON ---
    if command == 'ALL_LAMPU_ON':
        for idx in ['0', '1', '2']:
            kirim_serial(f'ON {idx}')
            client_mqtt.publish(TOPIC_STATUS, f'lampu_utama:ON' if idx=='0'
                                else f'lampu_kamar:ON' if idx=='1'
                                else f'lampu_tamu:ON')
            time.sleep(0.1)
        return

    # --- Kasus Khusus: SEMUA LAMPU OFF ---
    if command == 'ALL_LAMPU_OFF':
        for idx in ['0', '1', '2']:
            kirim_serial(f'OFF {idx}')
            client_mqtt.publish(TOPIC_STATUS, f'lampu_utama:OFF' if idx=='0'
                                else f'lampu_kamar:OFF' if idx=='1'
                                else f'lampu_tamu:OFF')
            time.sleep(0.1)
        return

    # --- Kasus Khusus: PERGI (matikan hampir semua) ---
    if command == 'ALL_OFF':
        semua_off = [
            ('OFF 0', 'lampu_utama:OFF'),
            ('OFF 1', 'lampu_kamar:OFF'),
            ('OFF 2', 'lampu_tamu:OFF'),
            ('OFF 3', 'colokan_terminal:OFF'),
            ('KIPASOFF', 'kipas:OFF'),
            ('OFF 7', 'pompa_penyiram:OFF'),
            ('OFF 8', 'solenoid_valve:OFF'),
        ]
        for cmd, status in semua_off:
            kirim_serial(cmd)
            client_mqtt.publish(TOPIC_STATUS, status)
            time.sleep(0.1)
        return

    # --- Perintah Normal ---
    kirim_serial(command)

    # Publish status ke Web
    if command in status_map:
        client_mqtt.publish(TOPIC_STATUS, status_map[command])

    # Pintu: auto-kunci kembali setelah 5 detik (sama seperti Arduino)
    if command == 'ON 9':
        def auto_lock():
            time.sleep(5.5)
            client_mqtt.publish(TOPIC_STATUS, 'solenoid_door:OFF')
            print("🔒 Pintu otomatis terkunci kembali")
        import threading
        threading.Thread(target=auto_lock, daemon=True).start()

# ==========================================
# 8. PROGRAM UTAMA
# ==========================================
def proses_perintah(inp):
    """Proses satu perintah teks, return response."""
    inp = inp.lower().strip()
    if not inp:
        return None, None

    base_response, tag = chatbot_response(inp)
    final_response     = base_response

    # --- Modifikasi respon untuk tag khusus ---

    if tag == 'jam':
        waktu          = datetime.datetime.now().strftime("%H:%M")
        final_response = f"Sekarang pukul {waktu}"

    elif tag == 'tanggal':
        tanggal        = datetime.datetime.now().strftime("%d %B %Y")
        final_response = f"Sekarang tanggal {tanggal}"

    elif tag == 'hari':
        try:
            locale.setlocale(locale.LC_TIME, 'id_ID.UTF-8')
        except:
            try:
                locale.setlocale(locale.LC_TIME, 'id_ID')
            except:
                pass
        hari           = datetime.datetime.now().strftime("%A")
        final_response = f"Hari ini adalah hari {hari}"

    elif tag == 'musik':
        final_response = "Baik, memutar musik di Youtube."
        webbrowser.open('https://www.youtube.com/watch?v=yKNxeF4KMsY')

    elif tag == 'suhu':
        if arduino:
            print("🌡️ Membaca sensor suhu dari Arduino...")
            t_end = time.time() + 3
            found = False
            while time.time() < t_end:
                if arduino.in_waiting:
                    line = arduino.readline().decode('utf-8', errors='ignore').strip()
                    if "temperature:" in line.lower():
                        try:
                            # Format dari Arduino: "temperature:28.50"
                            val  = float(line.split(":")[1])
                            suhu = int(val)
                            final_response = f"Suhu ruangan saat ini {suhu} derajat Celcius"
                            found = True
                            break
                        except:
                            continue
            if not found:
                final_response = "Maaf, data suhu belum terbaca dari sensor."
        else:
            final_response = "Maaf, sensor tidak terhubung saat ini."

    return final_response, tag


def start_assistant():
    print("\n" + "="*50)
    print("  🤖 ASISTEN SUARA PINTAR - RASPBERRY PI")
    print("="*50)
    speak("Sistem siap. Silakan berikan perintah.")

    while True:
        # ── Cek antrian perintah dari Web ──
        if web_command_queue:
            inp = web_command_queue.pop(0)
            print(f"\n🌐 Input dari Web: [{inp}]")
        else:
            time.sleep(0.1)
            continue

        if inp.lower() in ["berhenti", "keluar", "exit"]:
            speak("Sistem dimatikan. Sampai jumpa.")
            break

        # Proses perintah
        final_response, tag = proses_perintah(inp)
        if not final_response:
            continue

        print(f"🤖 Respon: {final_response}")

        # 1. Kirim balasan teks ke Web
        client_mqtt.publish(TOPIC_VOICE_REPLY, final_response)

        # 2. Ucapkan respon lewat speaker
        speak(final_response)

        # 3. Eksekusi hardware jika tag ada di mapping
        if tag in arduino_commands:
            command = arduino_commands[tag]
            send_to_arduino(tag, command)


if __name__ == "__main__":
    start_assistant()
