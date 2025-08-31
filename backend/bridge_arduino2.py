import serial
import requests
import time

# --- KONFIGURASI (WAJIB DISESUAIKAN) ---
ARDUINO_PORT = "COM3"  # <<< GANTI dengan port COM Arduino 2 Anda
BAUD_RATE = 115200
API_URL = "http://localhost:8000/sensors"

def main():
    print(f"Bridge 2: Menghubungkan ke Arduino Sensor di {ARDUINO_PORT}...")
    try:
        ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=2)
        time.sleep(2)
        print("Bridge 2: Terhubung.")
    except serial.SerialException as e:
        print(f"Bridge 2: Gagal terhubung: {e}")
        return

    while True:
        if ser.in_waiting > 0:
            try:
                line = ser.readline().decode('utf-8').strip()
                parts = line.split(',')

                if len(parts) == 5:
                    payload = {
                        "temperature": float(parts[0]),
                        "ldr_value": int(parts[1]),
                        "soil_moisture": int(parts[2]),
                        "lamp_status": parts[3],
                        "pump_status": parts[4]
                    }
                    requests.post(API_URL, json=payload)
                    print(f"Bridge 2: Mengirim data sensor -> {line}")
                else:
                    print(f"Bridge 2: Data tidak sesuai format (diterima {len(parts)}). Data: {line}")
            except Exception as e:
                print(f"Bridge 2: Terjadi error: {e}")
        time.sleep(1)

if __name__ == "__main__":
    main()
