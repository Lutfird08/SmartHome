# ==========================================
#  ASISTEN SUARA PINTAR - FINAL FIX (REPLY WEB)
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

# --- 1. KONFIGURASI MQTT ---
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_PREFIX = "lutfi_140910/smart_home/" 

TOPIC_REPLY  = MQTT_PREFIX + "voice_reply"
TOPIC_STATUS = MQTT_PREFIX + "status"
TOPIC_INPUT  = MQTT_PREFIX + "voice_input"

web_command_queue = [] 

def on_message(client, userdata, msg):
    text = msg.payload.decode("utf-8")
    print(f"📩 Terima dari Web: {text}")
    web_command_queue.append(text)

client_mqtt = mqtt.Client()
client_mqtt.on_message = on_message
client_mqtt.connect(MQTT_BROKER, MQTT_PORT, 60)
client_mqtt.subscribe(TOPIC_INPUT)
client_mqtt.loop_start()

# --- 2. KONFIGURASI SERIAL ARDUINO ---
SERIAL_PORT = 'COM3' # <--- PASTIKAN INI BENAR
BAUD_RATE = 115200

try:
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2) 
    print(f"✅ Berhasil terhubung ke Arduino di {SERIAL_PORT}")
except Exception as e:
    print(f"❌ Gagal terhubung ke Arduino: {e}")
    print("⚠️  Program berjalan dalam MODE SIMULASI")
    arduino = None

# --- 3. LOAD AI MODEL ---
try:
    lemmatizer = WordNetLemmatizer()
    model = load_model('model.h5')
    intents = json.loads(open("intents.json").read())
    words = pickle.load(open('words.pkl','rb'))
    classes = pickle.load(open('classes.pkl','rb'))
    print("✅ Model AI berhasil dimuat!")
except Exception as e:
    print(f"❌ Error Model AI: {e}")
    exit()

# --- 4. MAPPING PERINTAH ---
arduino_commands = {
    'lampu1_hidup': 'lampu1_hidup', 'lampu1_mati': 'lampu1_mati',
    'lampu2_hidup': 'lampu2_hidup', 'lampu2_mati': 'lampu2_mati',
    'lampu3_hidup': 'lampu3_hidup', 'lampu3_mati': 'lampu3_mati',
    'lampusemua_hidup': 'lampusemua_hidup', 'lampusemua_mati': 'lampusemua_mati',
    'terminal_hidup': 'terminal_hidup', 'terminal_mati': 'terminal_mati',
    'kran_hidup': 'kran_hidup', 'kran_mati': 'kran_mati',
    'pompa_hidup': 'pompa_hidup', 'pompa_mati': 'pompa_mati',
    'kipas_hidup': 'kipas_hidup', 'kipas_mati': 'kipas_mati',
    'kipas_naik': 'kipas_naik', 'kipas_turun': 'kipas_turun',
    'tirai_hidup': 'tirai_hidup', 'tirai_mati': 'tirai_mati',
    'kunci_mati': 'kunci_hidup', 'kunci_hidup': 'kunci_mati',
    'ac_hidup': 'ac_hidup', 'ac_mati': 'ac_mati',
    'ac_naik': 'ac_naik', 'ac_turun': 'ac_turun',
    'otopompa_hidup': 'otopompa_hidup', 'otopompa_mati': 'otopompa_mati',
    'otolampu_hidup': 'otolampu_hidup', 'otolampu_mati': 'otolampu_mati',
    'pergi': 'pergi'
}

# --- 5. FUNGSI NLP ---
def clean_up_sentence(sentence):
    sentence_words = nltk.word_tokenize(sentence)
    sentence_words = [lemmatizer.lemmatize(word.lower()) for word in sentence_words]
    return sentence_words

def bow(sentence, words, show_details=True):
    sentence_words = clean_up_sentence(sentence)
    bag = [0]*len(words)
    for s in sentence_words:
        for i,w in enumerate(words):
            if w == s: bag[i] = 1
    return(np.array(bag))

def predict_class(sentence, model):
    p = bow(sentence, words, show_details=False)
    res = model.predict(np.array([p]))[0]
    error = 0.25
    results = [[i, r] for i, r in enumerate(res) if r > error]
    results.sort(key=lambda x: x[1], reverse=True)
    return_list = []
    for r in results:
        return_list.append({"intent": classes[r[0]], "probability": str(r[1])})
    return return_list

def getResponse(ints, intents_json):
    if not ints: return "Maaf, saya tidak mengerti.", "unknown"
    tag = ints[0]['intent']
    list_of_intents = intents_json['intents']
    result = "Maaf, saya tidak mengerti."
    for i in list_of_intents:
        if i['tag'] == tag:
            result = random.choice(i['responses'])
            break
    return result, tag

def chatbot_response(text):
    ints = predict_class(text, model)
    res, tag = getResponse(ints, intents)
    # REVISI: Jangan kirim ke MQTT di sini dulu!
    # Kita kirim nanti setelah datanya lengkap (Jam/Tanggal/Suhu)
    return res, tag

# --- 6. FUNGSI SUARA ---
def speak(text):
    try:
        pygame.init(); pygame.mixer.init()
        tts_obj = gTTS(text=text, lang="id")
        mp3_fp = BytesIO()
        tts_obj.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        pygame.mixer.music.load(mp3_fp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
    except Exception as e:
        print(f"⚠️ Error TTS: {e}")

# --- 7. FUNGSI KOMUNIKASI ARDUINO ---
def send_to_arduino(command):
    status_map = {
        "lampu1_hidup": "Lampu Utama: ON",  "lampu1_mati": "Lampu Utama: OFF",
        "lampu2_hidup": "Lampu Kamar: ON",  "lampu2_mati": "Lampu Kamar: OFF",
        "lampu3_hidup": "Lampu Tamu: ON",   "lampu3_mati": "Lampu Tamu: OFF",
        "terminal_hidup": "Colokan Terminal: ON", "terminal_mati": "Colokan Terminal: OFF",
        "kipas_hidup": "Kipas: ON",         "kipas_mati": "Kipas: OFF",
        "ac_hidup": "AC: ON",               "ac_mati": "AC: OFF",
        "tirai_hidup": "Tirai Buka: ON",    "tirai_mati": "Tirai Tutup: ON",
        "kunci_hidup": "Solenoid Door: Terbuka", "kunci_mati": "Solenoid Door: Terkunci"
    }

    if arduino and arduino.is_open:
        full_command = command + '\n'
        arduino.write(full_command.encode())
        print(f"📤 Hardware: {command}")
        time.sleep(0.1)

    if command in status_map:
        msg_status = status_map[command]
        client_mqtt.publish(TOPIC_STATUS, msg_status)
    
    if command == "kunci_hidup": 
        time.sleep(5)
        client_mqtt.publish(TOPIC_STATUS, "Solenoid Door: Terkunci")

# --- 8. PROGRAM UTAMA ---
def start_assistant():
    print("\n🤖 === ASISTEN SUARA PINTAR SIAP === 🤖")
    speak("Sistem siap.")
    
    while True:
        # Cek Pesan dari Web
        if len(web_command_queue) > 0:
            inp = web_command_queue.pop(0).lower()
            print(f"🌐 Input Web: {inp}")
        else:
            inp = "none" 
            time.sleep(0.1)

        if inp == "none" or inp == "": continue
        if "berhenti" in inp: break
        
        # 1. Dapatkan Respon Dasar dari AI
        base_response, tag = chatbot_response(inp)
        
        # Variabel untuk menampung kalimat akhir yang akan dikirim ke Web
        final_response = base_response 
        
        # --- LOGIKA MODIFIKASI RESPON (AGAR LENGKAP DI WEB) ---
        
        # JAM
        if tag == 'jam':
            current_time = datetime.datetime.now().strftime("%H:%M")
            # Timpa respon template dengan data asli
            final_response = f"Sekarang pukul {current_time}"

        # TANGGAL
        elif tag == 'tanggal':
            current_date = datetime.datetime.now().strftime("%d %B %Y")
            final_response = f"Sekarang tanggal {current_date}"

        # HARI
        elif tag == 'hari':
            try:
                locale.setlocale(locale.LC_TIME, 'id_ID')
            except:
                pass
            current_day = datetime.datetime.now().strftime("%A")
            final_response = f"Hari ini adalah hari {current_day}"

        # MUSIK
        elif tag == 'musik':
            final_response = "Baik, memutar musik di Youtube."
            youtube_link = 'https://www.youtube.com/watch?v=yKNxeF4KMsY'
            webbrowser.open(youtube_link)

        # SUHU (SENSOR)
        elif tag == 'suhu':
            if arduino:
                print("🌡️ Membaca sensor suhu...")
                t_end = time.time() + 2 
                found = False
                
                while time.time() < t_end:
                    if arduino.in_waiting:
                        line = arduino.readline().decode('utf-8', errors='ignore').strip()
                        # Format: "SENSOR: ... Temp:28.00"
                        if "Temp:" in line:
                            try:
                                parts = line.split("Temp:")
                                temp_val = float(parts[1])
                                temp_int = int(temp_val)
                                final_response = f"Suhu ruangan saat ini {temp_int} derajat Celcius"
                                found = True
                                break
                            except:
                                continue
                if not found:
                    final_response = "Maaf, data suhu belum terbaca."
            else:
                final_response = "Maaf, sensor tidak terhubung."

        # --- KIRIM KE WEB & BICARA ---
        # Sekarang 'final_response' sudah berisi data lengkap (bukan template lagi)
        
        print(f"🤖 Bot: {final_response}")
        
        # 1. Kirim Teks Lengkap ke Web
        client_mqtt.publish(TOPIC_REPLY, final_response)
        
        # 2. Bicara di Laptop
        speak(final_response)
        
        # 3. Eksekusi Hardware (Lampu, AC, dll)
        if tag in arduino_commands:
            cmd = arduino_commands[tag]
            send_to_arduino(cmd)

if __name__ == "__main__":
    start_assistant()