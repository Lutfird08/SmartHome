# ==========================================
#  ASISTEN SUARA PINTAR - MODE SIMULASI
#  Fix: Bertindak sebagai Virtual ESP32
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
import threading
import paho.mqtt.client as mqtt

# ==========================================
# 1. KONFIGURASI MQTT
# ==========================================
MQTT_BROKER  = "broker.emqx.io"
MQTT_PORT    = 1883

TOPIC_CONTROL     = "smart_home/control"       
TOPIC_STATUS      = "smart_home/status"        
TOPIC_SENSOR      = "smart_home/sensor"        
TOPIC_VOICE_INPUT = "smart_home/voice_input"   
TOPIC_VOICE_REPLY = "smart_home/voice_reply"   
TOPIC_REQUEST     = "smart_home/request"       

web_command_queue = []

# --- MEMORI LOKAL STATUS PERANGKAT ---
current_device_states = {
    'lampu_utama': 'OFF',
    'lampu_kamar': 'OFF',
    'lampu_tamu': 'OFF',
    'colokan_terminal': 'OFF',
    'kipas': 'OFF',
    'pompa_penyiram': 'OFF',
    'solenoid_valve': 'OFF',
    'solenoid_door': 'OFF',
    'tirai': 'BUKA',
    'ac_power': 'OFF',
    'otomatis_pompa': 'OFF',
    'otomatis_lampu': 'OFF'
}

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ MQTT Terhubung ke broker!")
        client.subscribe(TOPIC_VOICE_INPUT)
        client.subscribe(TOPIC_REQUEST)
        # PERBAIKAN: Python ikut mendengarkan klik tombol dari UI web (sebagai ganti ESP32)
        client.subscribe(TOPIC_CONTROL) 
        print(f"👂 Mendengarkan topik:\n - {TOPIC_VOICE_INPUT}\n - {TOPIC_REQUEST}\n - {TOPIC_CONTROL}")
    else:
        print(f"❌ Gagal konek MQTT, kode: {rc}")

def on_message(client, userdata, msg):
    topic = msg.topic
    text = msg.payload.decode("utf-8").strip()
    
    if topic == TOPIC_VOICE_INPUT:
        print(f"📩 Perintah suara dari Web: [{text}]")
        if text:
            web_command_queue.append(text)
            
    elif topic == TOPIC_REQUEST:
        print("🔄 Web berpindah halaman. Sinkronisasi status dikirim...")
        for device, state in current_device_states.items():
            client_mqtt.publish(TOPIC_STATUS, f"{device}:{state} (SYNC)")
            time.sleep(0.02)
            
    # PERBAIKAN: Jika ada klik tombol manual dari web
    elif topic == TOPIC_CONTROL:
        print(f"🎛️ [TOMBOL MANUAL UI] Menerima perintah: {text}")
        
        # Konversi sinyal AC manual agar dikenali oleh logika memori Python
        if text == "AC_POWER":
            text = "AC_POWER_ON" if current_device_states['ac_power'] == 'OFF' else "AC_POWER_OFF"
            
        # Eksekusi dan perbarui memori
        send_to_arduino("manual", text)

client_mqtt = mqtt.Client(client_id="raspi_assistant_sim_" + str(random.randint(1000,9999)))
client_mqtt.on_connect = on_connect
client_mqtt.on_message = on_message

try:
    client_mqtt.connect(MQTT_BROKER, MQTT_PORT, 60)
    client_mqtt.loop_start()
    print("✅ MQTT client dimulai")
except Exception as e:
    print(f"❌ Gagal konek MQTT: {e}")

# ==========================================
# 2. KONFIGURASI SERIAL (DIMATIKAN UNTUK SIMULASI)
# ==========================================
arduino = None 
print("⚠️  Berjalan dalam MODE SIMULASI (tanpa hardware fisik)")

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
# 4. MAPPING PERINTAH AI
# ==========================================
arduino_commands = {
    'lampu1_hidup':      'ON 0',           
    'lampu1_mati':       'OFF 0',
    'lampu2_hidup':      'ON 1',           
    'lampu2_mati':       'OFF 1',
    'lampu3_hidup':      'ON 2',           
    'lampu3_mati':       'OFF 2',
    'lampusemua_hidup':  'ALL_LAMPU_ON',   
    'lampusemua_mati':   'ALL_LAMPU_OFF',
    'terminal_hidup':    'ON 3',
    'terminal_mati':     'OFF 3',
    'kipas_hidup':       'KIPASON 50',
    'kipas_mati':        'KIPASOFF',
    'kipas_naik':        'KIPASON 100',    
    'kipas_turun':       'KIPASON 33',     
    'pompa_hidup':       'ON 7',
    'pompa_mati':        'OFF 7',
    'kran_hidup':        'ON 8',
    'kran_mati':         'OFF 8',
    'kunci_mati':        'ON 9',           
    'kunci_hidup':       'OFF 9',          
    'tirai_hidup':       'TIRAITUTUP 45',  
    'tirai_mati':        'TIRAIBUKA 45',   
    'ac_hidup':          'AC_POWER_ON',  
    'ac_mati':           'AC_POWER_OFF',       
    'ac_naik':           'AC_UP',
    'ac_turun':          'AC_DOWN',
    'otopompa_hidup':    'ON 10',
    'otopompa_mati':     'OFF 10',
    'otolampu_hidup':    'ON 11',
    'otolampu_mati':     'OFF 11',
    'pergi':             'ALL_OFF',        
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
# 7. FUNGSI KIRIM PERINTAH
# ==========================================
status_map = {
    'ON 0':        'lampu_utama:ON',
    'OFF 0':       'lampu_utama:OFF',
    'ON 1':        'lampu_kamar:ON',
    'OFF 1':       'lampu_kamar:OFF',
    'ON 2':        'lampu_tamu:ON',
    'OFF 2':       'lampu_tamu:OFF',
    'ON 3':        'colokan_terminal:ON',
    'OFF 3':       'colokan_terminal:OFF',
    'KIPASON 33':  'kipas:ON',
    'KIPASON 50':  'kipas:ON',
    'KIPASON 66':  'kipas:ON',
    'KIPASON 100': 'kipas:ON',
    'KIPASOFF':    'kipas:OFF',
    'ON 7':        'pompa_penyiram:ON',
    'OFF 7':       'pompa_penyiram:OFF',
    'ON 8':        'solenoid_valve:ON',
    'OFF 8':       'solenoid_valve:OFF',
    'ON 9':        'solenoid_door:ON',
    'OFF 9':       'solenoid_door:OFF',
    'TIRAIBUKA 45':'tirai:BUKA',
    'TIRAITUTUP 45':'tirai:TUTUP',
    'TIRAIOFF':    'tirai:STOP',
    'AC_POWER_ON': 'ac_power:ON',
    'AC_POWER_OFF':'ac_power:OFF',
    'ON 10':       'otomatis_pompa:ON',
    'OFF 10':      'otomatis_pompa:OFF',
    'ON 11':       'otomatis_lampu:ON',
    'OFF 11':      'otomatis_lampu:OFF',
}

def kirim_serial(command):
    if arduino and arduino.is_open:
        if command == 'AC_POWER_ON' or command == 'AC_POWER_OFF':
            arduino.write(('AC_POWER\n').encode())
        else:
            arduino.write((command + '\n').encode())
        time.sleep(0.15)
    else:
        # Hapus tampilan [SIMULASI] jika pemicunya adalah tombol UI agar terminal tidak berantakan
        pass 

def send_to_arduino(tag, command):
    
    # Update memori
    if command in status_map:
        parts = status_map[command].split(':')
        if len(parts) == 2:
            current_device_states[parts[0]] = parts[1]

    # --- Kasus Khusus ---
    if command == 'ALL_LAMPU_ON':
        for idx, dev in zip(['0', '1', '2'], ['lampu_utama', 'lampu_kamar', 'lampu_tamu']):
            current_device_states[dev] = 'ON'
            kirim_serial(f'ON {idx}')
            client_mqtt.publish(TOPIC_STATUS, f'{dev}:ON')
            time.sleep(0.1)
        return

    if command == 'ALL_LAMPU_OFF':
        for idx, dev in zip(['0', '1', '2'], ['lampu_utama', 'lampu_kamar', 'lampu_tamu']):
            current_device_states[dev] = 'OFF'
            kirim_serial(f'OFF {idx}')
            client_mqtt.publish(TOPIC_STATUS, f'{dev}:OFF')
            time.sleep(0.1)
        return

    if command == 'ALL_OFF':
        semua_off = [
            ('OFF 0', 'lampu_utama'), ('OFF 1', 'lampu_kamar'),
            ('OFF 2', 'lampu_tamu'), ('OFF 3', 'colokan_terminal'),
            ('KIPASOFF', 'kipas'), ('OFF 7', 'pompa_penyiram'),
            ('OFF 8', 'solenoid_valve')
        ]
        for cmd, dev in semua_off:
            current_device_states[dev] = 'OFF'
            kirim_serial(cmd)
            client_mqtt.publish(TOPIC_STATUS, f"{dev}:OFF")
            time.sleep(0.1)
        return

    kirim_serial(command)

    # Kirim status balik ke Web agar semua halaman lain tahu
    if command in status_map:
        client_mqtt.publish(TOPIC_STATUS, status_map[command])

    if command == 'ON 9':
        def auto_lock():
            time.sleep(5.5)
            current_device_states['solenoid_door'] = 'OFF'
            client_mqtt.publish(TOPIC_STATUS, 'solenoid_door:OFF')
            print("🔒 [SIMULASI] Pintu otomatis terkunci kembali")
        threading.Thread(target=auto_lock, daemon=True).start()

# ==========================================
# 8. PROGRAM UTAMA
# ==========================================
def proses_perintah(inp):
    inp = inp.lower().strip()
    if not inp:
        return None, None

    base_response, tag = chatbot_response(inp)
    final_response     = base_response

    if tag == 'jam':
        waktu          = datetime.datetime.now().strftime("%H:%M")
        final_response = f"Sekarang pukul {waktu}"
    elif tag == 'tanggal':
        tanggal        = datetime.datetime.now().strftime("%d %B %Y")
        final_response = f"Sekarang tanggal {tanggal}"
    elif tag == 'suhu':
        suhu_simulasi = random.randint(24, 29)
        final_response = f"Suhu ruangan saat ini {suhu_simulasi} derajat Celcius"

    return final_response, tag


def start_assistant():
    print("\n" + "="*50)
    print("  🤖 ASISTEN SUARA PINTAR - MODE SIMULASI")
    print("="*50)
    speak("Sistem siap. Silakan berikan perintah.")

    while True:
        if web_command_queue:
            inp = web_command_queue.pop(0)
        else:
            time.sleep(0.1)
            continue

        if inp.lower() in ["berhenti", "keluar", "exit"]:
            speak("Sistem dimatikan. Sampai jumpa.")
            break

        final_response, tag = proses_perintah(inp)
        if not final_response:
            continue

        print(f"🤖 Respon AI: {final_response}")

        if tag in arduino_commands:
            command = arduino_commands[tag]
            send_to_arduino(tag, command)

        client_mqtt.publish(TOPIC_VOICE_REPLY, final_response)
        speak(final_response)


if __name__ == "__main__":
    start_assistant()