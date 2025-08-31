import serial
import requests
import time
import json

# --- KONFIGURASI (WAJIB DISESUAIKAN) ---
ARDUINO_PORT = "COM7"  # <<< GANTI dengan port COM Arduino 1 Anda
BAUD_RATE = 115200
API_URL = "http://localhost:8000/arduino"

def main():
    print(f"Bridge 1: Menghubungkan ke Arduino Kontroler di {ARDUINO_PORT}...")
    try:
        ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=2)
        time.sleep(2)
        print("Bridge 1: Terhubung.")
    except serial.SerialException as e:
        print(f"Bridge 1: Gagal terhubung: {e}")
        return

    while True:
        if ser.in_waiting > 0:
            try:
                line = ser.readline().decode('utf-8').strip()
                parts = line.split(',')
                
                if len(parts) == 13:
                    payload = {
                        "lamp_one": parts[0],
                        "lamp_two": parts[1],
                        "lamp_three": parts[2],
                        "terminal": parts[3],
                        "fan": {
                            "status": parts[10],
                            "speed": "one" if parts[11] == "1" else ("two" if parts[11] == "2" else "three")
                        },
                        "tirai_left": parts[4], 
                        "tirai_right": parts[4],
                        "ac": { "status": parts[12], "temperature": 24 }
                    }
                    requests.post(API_URL, json=payload)
                    print(f"Bridge 1: Mengirim status kontroler -> {line}")
                else:
                    print(f"Bridge 1: Data tidak sesuai format (diterima {len(parts)}). Data: {line}")
            except Exception as e:
                print(f"Bridge 1: Terjadi error: {e}")
        time.sleep(1)

if __name__ == "__main__":
    main()
