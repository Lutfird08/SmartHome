# ==========================================
#  ASISTEN SUARA PINTAR - OFFLINE MODE
#  (Cocok dengan MAKET_RELAY_ARDUINO_MEGA)
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

# --- 1. KONFIGURASI SERIAL ARDUINO ---
SERIAL_PORT = 'COM3' # <--- PASTIKAN PORT INI BENAR (Cek di Device Manager)
BAUD_RATE = 115200

try:
    arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2) 
    print(f"✅ Berhasil terhubung ke Arduino di {SERIAL_PORT}")
except Exception as e:
    print(f"❌ Gagal terhubung ke Arduino: {e}")
    print("⚠️  Program berjalan dalam MODE SIMULASI")
    arduino = None

# --- 2. LOAD AI MODEL ---
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

# --- 3. MAPPING PERINTAH (Versi Maket) ---
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
    'kipas_hidup':       'KIPASON 80',
    'kipas_mati':        'KIPASOFF',
    'kipas_naik':        'KIPASON 100',    
    'kipas_turun':       'KIPASON 60',     
    'pompa_hidup':       'ON 7',
    'pompa_mati':        'OFF 7',
    'kran_hidup':        'ON 8',
    'kran_mati':         'OFF 8',
    'kunci_mati':        'ON 9',           
    'kunci_hidup':       'OFF 9',          
    'tirai_hidup':       'TIRAITUTUP 73',  
    'tirai_mati':        'TIRAIBUKA 55',   
    'ac_hidup':          'AC_POWER',  
    'ac_mati':           'AC_POWER',       
    'ac_naik':           'AC_UP',
    'ac_turun':          'AC_DOWN',
    'otopompa_hidup':    'ON 10',
    'otopompa_mati':     'OFF 10',
    'otolampu_hidup':    'ON 11',
    'otolampu_mati':     'OFF 11',
    'pergi':             'ALL_OFF',        
}

# --- 4. FUNGSI NLP ---
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
    return res, tag

# --- 5. FUNGSI INPUT & OUTPUT SUARA ---
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

def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("\n🎤 Silakan bicara...")
        r.adjust_for_ambient_noise(source, duration=0.5)
        audio = r.listen(source)
    
    try:
        text = r.recognize_google(audio, language="id-ID")
        print(f"🗣️ Anda: {text}")
        return text.lower()
    except sr.UnknownValueError:
        print("...")
        return ""
    except sr.RequestError:
        print("❌ Error koneksi Google Speech")
        return ""

# --- 6. FUNGSI KOMUNIKASI ARDUINO ---
def send_to_arduino(command):
    if not (arduino and arduino.is_open):
        return
        
    # --- Penanganan Perintah Jamak (Multi-Command) ---
    if command == 'ALL_LAMPU_ON':
        for idx in ['0', '1', '2']:
            arduino.write((f'ON {idx}\n').encode())
            print(f"📤 Hardware: ON {idx}")
            time.sleep(0.15)
        return
        
    if command == 'ALL_LAMPU_OFF':
        for idx in ['0', '1', '2']:
            arduino.write((f'OFF {idx}\n').encode())
            print(f"📤 Hardware: OFF {idx}")
            time.sleep(0.15)
        return
        
    if command == 'ALL_OFF':
        cmds = ['OFF 0', 'OFF 1', 'OFF 2', 'OFF 3', 'KIPASOFF', 'OFF 7', 'OFF 8']
        for cmd in cmds:
            arduino.write((cmd + '\n').encode())
            print(f"📤 Hardware: {cmd}")
            time.sleep(0.15)
        return

    # --- Penanganan Perintah Tunggal ---
    full_command = command + '\n'
    arduino.write(full_command.encode())
    print(f"📤 Hardware: {command}")
    time.sleep(0.1)

# --- 7. PROGRAM UTAMA ---
def start_assistant():
    print("\n🤖 === ASISTEN OFFLINE SIAP === 🤖")
    speak("Sistem offline siap digunakan.")
    
    while True:
        # 1. Mendengarkan Suara
        inp = listen()
        
        # Jika ingin pakai ketikan keyboard sebagai alternatif, uncomment baris bawah:
        # inp = input("Ketik perintah: ").lower()

        if inp == "": continue
        if "berhenti" in inp or "keluar" in inp: 
            speak("Sampai jumpa.")
            break
        
        # 2. Dapatkan Respon Dasar dari AI
        base_response, tag = chatbot_response(inp)
        
        # Variabel untuk kalimat akhir
        final_response = base_response 
        
        # --- LOGIKA MODIFIKASI RESPON ---
        
        # JAM
        if tag == 'jam':
            current_time = datetime.datetime.now().strftime("%H:%M")
            final_response = f"Sekarang pukul {current_time}"

        # TANGGAL
        elif tag == 'tanggal':
            current_date = datetime.datetime.now().strftime("%d %B %Y")
            final_response = f"Sekarang tanggal {current_date}"

        # HARI
        elif tag == 'hari':
            try: locale.setlocale(locale.LC_TIME, 'id_ID')
            except: pass
            current_day = datetime.datetime.now().strftime("%A")
            final_response = f"Hari ini adalah hari {current_day}"

        # MUSIK
        elif tag == 'musik':
            final_response = "Baik, memutar musik."
            youtube_link = 'https://www.youtube.com/watch?v=yKNxeF4KMsY'
            webbrowser.open(youtube_link)

        # SUHU (SENSOR) - Perbaikan format 'temperature:'
        elif tag == 'suhu':
            if arduino:
                print("🌡️ Membaca sensor suhu...")
                t_end = time.time() + 2 
                found = False
                while time.time() < t_end:
                    if arduino.in_waiting:
                        line = arduino.readline().decode('utf-8', errors='ignore').strip()
                        if "temperature:" in line.lower():
                            try:
                                parts = line.lower().split("temperature:")
                                temp_val = float(parts[1])
                                temp_int = int(temp_val)
                                final_response = f"Suhu ruangan saat ini {temp_int} derajat Celcius"
                                found = True
                                break
                            except: continue
                if not found: final_response = "Maaf, data suhu belum terbaca."
            else:
                final_response = "Maaf, sensor tidak terhubung."

        # --- EKSEKUSI ---
        
        print(f"🤖 Bot: {final_response}")
        
        # Eksekusi Hardware terlebih dahulu agar meminimalisir delay
        if tag in arduino_commands:
            cmd = arduino_commands[tag]
            send_to_arduino(cmd)
            
        speak(final_response)

if __name__ == "__main__":
    start_assistant()