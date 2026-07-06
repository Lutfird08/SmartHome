# ==========================================
#  ASISTEN SUARA PINTAR - WIRELESS ESP32 MODE
#  Arsitektur "Satu Pintu": Semua lewat MQTT
# ==========================================

import warnings
warnings.filterwarnings("ignore")

import nltk
from nltk.stem import WordNetLemmatizer
import json
import pickle
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

# Memori Status & Suhu (Didapat murni dari laporan ESP32 via MQTT)
current_device_states = {
    'lampu_utama': 'OFF', 'lampu_kamar': 'OFF', 'lampu_tamu': 'OFF',
    'colokan_terminal': 'OFF', 'kipas': 'OFF', 'pompa_penyiram': 'OFF',
    'solenoid_valve': 'OFF', 'solenoid_door': 'OFF', 'tirai': 'BUKA',
    'ac_power': 'OFF', 'otomatis_pompa': 'OFF', 'otomatis_lampu': 'OFF'
}
current_temperature = None

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ MQTT Terhubung! (Mode Wireless ESP32)")
        client.subscribe(TOPIC_VOICE_INPUT)
        client.subscribe(TOPIC_REQUEST)
        client.subscribe(TOPIC_STATUS) 
        client.subscribe(TOPIC_SENSOR) # Dengarkan Suhu dari ESP32
    else:
        print(f"❌ Gagal konek MQTT, kode: {rc}")

def on_message(client, userdata, msg):
    global current_temperature
    topic = msg.topic
    text = msg.payload.decode("utf-8").strip()
    
    if topic == TOPIC_VOICE_INPUT:
        print(f"📩 Perintah dari Web: [{text}]")
        if text:
            web_command_queue.append(text)
            
    elif topic == TOPIC_REQUEST:
        for device, state in current_device_states.items():
            client_mqtt.publish(TOPIC_STATUS, f"{device}:{state} (SYNC)")
            time.sleep(0.02)
            
    elif topic == TOPIC_STATUS:
        # Catat status nyata dari Hardware/ESP32
        if "(SYNC)" not in text and ":" in text:
            parts = text.split(':')
            if len(parts) == 2:
                device_name = parts[0].strip().lower()
                device_state = parts[1].strip().upper()
                if device_name in current_device_states:
                    current_device_states[device_name] = device_state
                    
    elif topic == TOPIC_SENSOR:
        # Menangkap data suhu dari Arduino -> ESP32 -> MQTT
        if "temperature" in text.lower():
            try:
                # Format: "temperature:28.50:60.00"
                val  = float(text.split(":")[1])
                current_temperature = int(val)
            except:
                pass

client_mqtt = mqtt.Client(client_id="raspi_assistant_wireless_" + str(random.randint(1000,9999)))
client_mqtt.on_connect = on_connect
client_mqtt.on_message = on_message

try:
    client_mqtt.connect(MQTT_BROKER, MQTT_PORT, 60)
    client_mqtt.loop_start()
except Exception as e:
    print(f"❌ Gagal konek MQTT: {e}")

# ==========================================
# 2. LOAD MODEL AI
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

arduino_commands = {
    'lampu1_hidup': 'ON 0', 'lampu1_mati': 'OFF 0',
    'lampu2_hidup': 'ON 1', 'lampu2_mati': 'OFF 1',
    'lampu3_hidup': 'ON 2', 'lampu3_mati': 'OFF 2',
    'lampusemua_hidup': 'ALL_LAMPU_ON', 'lampusemua_mati': 'ALL_LAMPU_OFF',
    'terminal_hidup': 'ON 3', 'terminal_mati': 'OFF 3',
    'kipas_hidup': 'KIPASON 50', 'kipas_mati': 'KIPASOFF',
    'kipas_naik': 'KIPASON 100', 'kipas_turun': 'KIPASON 33',
    'pompa_hidup': 'ON 7', 'pompa_mati': 'OFF 7',
    'kran_hidup': 'ON 8', 'kran_mati': 'OFF 8',
    'kunci_mati': 'ON 9', 'kunci_hidup': 'OFF 9',
    'tirai_hidup': 'TIRAITUTUP 45', 'tirai_mati': 'TIRAIBUKA 45',
    'ac_hidup': 'AC_POWER', 'ac_mati': 'AC_POWER',       
    'ac_naik': 'AC_UP', 'ac_turun': 'AC_DOWN',
    'otopompa_hidup': 'ON 10', 'otopompa_mati': 'OFF 10',
    'otolampu_hidup': 'ON 11', 'otolampu_mati': 'OFF 11',
    'pergi': 'ALL_OFF',        
}

# ==========================================
# FUNGSI NLP & SUARA
# ==========================================
def clean_up_sentence(sentence):
    sentence_words = nltk.word_tokenize(sentence)
    sentence_words = [lemmatizer.lemmatize(w.lower()) for w in sentence_words]
    return sentence_words

def bow(sentence, words):
    bag = [0] * len(words)
    for s in clean_up_sentence(sentence):
        for i, w in enumerate(words):
            if w == s: bag[i] = 1
    return np.array(bag)

def chatbot_response(text):
    p = bow(text, words)
    res = model.predict(np.array([p]), verbose=0)[0]
    results = [[i, r] for i, r in enumerate(res) if r > 0.25]
    results.sort(key=lambda x: x[1], reverse=True)
    ints = [{"intent": classes[r[0]], "probability": str(r[1])} for r in results]
    
    if not ints: return "Maaf, saya tidak mengerti.", "unknown"
    tag = ints[0]['intent']
    for i in intents['intents']:
        if i['tag'] == tag: return random.choice(i['responses']), tag
    return "Maaf, saya tidak mengerti.", "unknown"

def speak(text):
    try:
        pygame.mixer.init()
        tts = gTTS(text=text, lang="id", slow=False)
        mp3_fp = BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        pygame.mixer.music.load(mp3_fp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except:
        pass

# ==========================================
# PUSAT KONTROL ALAT VIA MQTT -> ESP32
# ==========================================
def send_to_esp32(command):
    # Kasus Khusus untuk perintah jamak
    if command == 'ALL_LAMPU_ON':
        for idx in ['0', '1', '2']:
            client_mqtt.publish(TOPIC_CONTROL, f'ON {idx}')
            time.sleep(0.15)
        return
    if command == 'ALL_LAMPU_OFF':
        for idx in ['0', '1', '2']:
            client_mqtt.publish(TOPIC_CONTROL, f'OFF {idx}')
            time.sleep(0.15)
        return
    if command == 'ALL_OFF':
        cmds = ['OFF 0', 'OFF 1', 'OFF 2', 'OFF 3', 'KIPASOFF', 'OFF 7', 'OFF 8']
        for cmd in cmds:
            client_mqtt.publish(TOPIC_CONTROL, cmd)
            time.sleep(0.15)
        return

    # Kirim perintah tunggal ke topik control, ESP32 yang akan tangkap dan eksekusi!
    client_mqtt.publish(TOPIC_CONTROL, command)
    print(f"📡 Perintah dikirim ke ESP32: {command}")

# ==========================================
# PROGRAM UTAMA
# ==========================================
def start_assistant():
    print("\n" + "="*50)
    print("  🤖 ASISTEN SUARA - WIRELESS ESP32 MODE")
    print("="*50)
    speak("Sistem siap. Silakan berikan perintah.")

    while True:
        if web_command_queue:
            inp = web_command_queue.pop(0)
            print(f"\n🌐 Input Web: [{inp}]")
        else:
            time.sleep(0.1)
            continue

        if inp.lower() in ["berhenti", "keluar", "exit"]:
            speak("Sistem dimatikan. Sampai jumpa.")
            break

        final_response, tag = chatbot_response(inp)
        
        # Proses Fitur Khusus
        if tag == 'jam':
            final_response = f"Sekarang pukul {datetime.datetime.now().strftime('%H:%M')}"
        elif tag == 'tanggal':
            final_response = f"Sekarang tanggal {datetime.datetime.now().strftime('%d %B %Y')}"
        elif tag == 'suhu':
            if current_temperature is not None:
                final_response = f"Suhu ruangan saat ini {current_temperature} derajat Celcius"
            else:
                final_response = "Maaf, data suhu belum terbaca dari perangkat ESP."

        if not final_response:
            continue

        print(f"🤖 Respon AI: {final_response}")

        # Tembak perintah ke ESP32 via MQTT (Tanpa Kabel USB!)
        if tag in arduino_commands:
            command = arduino_commands[tag]
            send_to_esp32(command)

        client_mqtt.publish(TOPIC_VOICE_REPLY, final_response)
        speak(final_response)

if __name__ == "__main__":
    start_assistant()