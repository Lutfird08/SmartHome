import sqlite3
import json
import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os.path
from pathlib import Path
import subprocess

# --- Pydantic Models ---
class ChatRequest(BaseModel):
    chat: str

class ArduinoItem(BaseModel):
    lamp_one: str
    lamp_two: str
    lamp_three: str
    terminal: str
    fan: object
    tirai_left: str
    tirai_right: str
    ac: object

class Password(BaseModel):
    password: str

# Model data baru untuk menerima data dari Arduino Sensor Hub (Arduino 2)
class SensorData(BaseModel):
    temperature: float
    ldr_value: int
    soil_moisture: int
    lamp_status: str
    pump_status: str

# --- Lifespan Manager (Inisialisasi Aplikasi) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Membuat file database jika belum ada
    if not os.path.isfile('./database.db'):
        Path('./database.db').touch()

    conn = get_database_connection()
    
    # Membuat tabel 'devices' untuk Arduino 1 (kontroler)
    conn.execute('''CREATE TABLE IF NOT EXISTS devices (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_name TEXT NOT NULL UNIQUE,
                        status BOOLEAN NOT NULL,
                        additional_status TEXT
                    )''')
    conn.execute('''INSERT OR IGNORE INTO devices (device_name, status) VALUES
                    ('lamp_one', 0), ('lamp_two', 0), ('lamp_three', 0), ('terminal', 0), 
                    ('fan', 0), ('tirai', 0), ('ac', 0), ('door', 0), ('plant', 0),
                    ('valve', 0), ('lock', 0), ('auto_lamp', 0), ('auto_pump', 0),
                    ('pump', 0), ('mode_pergi', 0), ('lamp_all', 0)
                ''')

    # Membuat tabel 'sensors' untuk Arduino 2 (sensor hub)
    conn.execute('''CREATE TABLE IF NOT EXISTS sensors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                        temperature REAL NOT NULL,
                        ldr_value INTEGER NOT NULL,
                        soil_moisture INTEGER NOT NULL,
                        lamp_status TEXT NOT NULL,
                        pump_status TEXT NOT NULL
                    )''')

    conn.commit()
    conn.close()

    yield

# --- Inisialisasi Aplikasi FastAPI ---
app = FastAPI(lifespan=lifespan,
              openapi_version="3.0.2")

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Fungsi Utilitas Database ---
def get_database_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def changeStatusBool(num):
    return num == 1

# --- Endpoint Baru untuk Arduino Sensor Hub (Arduino 2) ---
@app.post("/sensors")
async def receive_sensor_data(data: SensorData):
    """
    Menerima dan menyimpan data sensor dari Arduino 2 ke dalam database.
    """
    conn = get_database_connection()
    conn.execute(
        "INSERT INTO sensors (temperature, ldr_value, soil_moisture, lamp_status, pump_status) VALUES (?, ?, ?, ?, ?)",
        (data.temperature, data.ldr_value, data.soil_moisture, data.lamp_status, data.pump_status)
    )
    conn.commit()
    conn.close()
    print(f"Menerima data sensor: {data.dict()}")
    return {"message": "Sensor data received successfully"}

@app.get("/sensors")
async def get_latest_sensor_data():
    """
    Mengambil data sensor terakhir dari database.
    """
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sensors ORDER BY timestamp DESC LIMIT 1")
    latest_data = cursor.fetchone()
    conn.close()

    if not latest_data:
        raise HTTPException(status_code=404, detail="No sensor data available yet.")
    
    # Mengubah hasil dari database menjadi dictionary
    return dict(latest_data)

# --- Endpoint yang Sudah Ada ---

@app.post("/password")
async def send_and_check_password(password: Password):
    if password.password == "lutfi123":
        return {'message': 'login success'}
    raise HTTPException(
        status_code=401,
        detail='wrong password, please try again'
    )

@app.post("/arduino")
async def arduino_post(arduino_items: ArduinoItem):
    def strToBool(str_val):
        return str_val == "on"

    conn = get_database_connection()
    cursor = conn.cursor()

    # Update device statuses based on incoming data
    cursor.execute("UPDATE devices SET status = ? WHERE device_name = 'lamp_one'", (strToBool(arduino_items.lamp_one),))
    cursor.execute("UPDATE devices SET status = ? WHERE device_name = 'lamp_two'", (strToBool(arduino_items.lamp_two),))
    cursor.execute("UPDATE devices SET status = ? WHERE device_name = 'lamp_three'", (strToBool(arduino_items.lamp_three),))
    cursor.execute("UPDATE devices SET status = ? WHERE device_name = 'terminal'", (strToBool(arduino_items.terminal),))
    tirai_status = strToBool(arduino_items.tirai_left) or strToBool(arduino_items.tirai_right)
    cursor.execute("UPDATE devices SET status = ? WHERE device_name = 'tirai'", (tirai_status,))

    # Fan code
    json_fan = arduino_items.fan
    cursor.execute("UPDATE devices SET status = ? WHERE device_name = 'fan'", (strToBool(json_fan['status']),))
    cursor.execute("UPDATE devices SET additional_status = ? WHERE device_name = 'fan'",
                   (json.dumps({"speed": json_fan['speed']}),))

    # AC code
    json_ac = arduino_items.ac
    cursor.execute("UPDATE devices SET status = ? WHERE device_name = 'ac'", (strToBool(json_ac['status']),))
    cursor.execute("UPDATE devices SET additional_status = ? WHERE device_name = 'ac'",
                   (json.dumps({"temperature": json_ac['temperature']}),))

    conn.commit()
    conn.close()
    return {"message": "Device statuses updated successfully"}

@app.get('/arduino')
async def arduino_get():
    # ... (Sisa fungsi ini tetap sama dengan versi Anda, atau bisa disederhanakan seperti sebelumnya)
    # Untuk menjaga konsistensi, kita akan gunakan kode yang sudah ada dari file Anda.
    conn = get_database_connection()
    cursor = conn.cursor()

    def get_status(device_name):
        cursor.execute("SELECT status FROM devices WHERE device_name = ?", (device_name,))
        row = cursor.fetchone()
        return changeStatusBool(row['status']) if row else None
    
    lamp_status = []
    cursor.execute("SELECT status FROM devices WHERE device_name LIKE 'lamp%'")
    lamp_rows = cursor.fetchall()
    for row in lamp_rows:
        lamp_status.append(changeStatusBool(row[0]))

    fan_status = {}
    cursor.execute("SELECT status, additional_status FROM devices WHERE device_name = 'fan'")
    fan = cursor.fetchone()
    if fan and fan['additional_status']:
        speed = json.loads(fan['additional_status']).get('speed')
        fan_status = {
            "condition": changeStatusBool(fan['status']),
            "speed": {"one": 1, "two": 2, "three": 3}.get(speed, 0)
        }
        
    ac_status = {}
    cursor.execute("SELECT status, additional_status FROM devices WHERE device_name = 'ac'")
    ac = cursor.fetchone()
    if ac and ac['additional_status']:
        temperature = json.loads(ac['additional_status']).get('temperature')
        ac_status = {
            "condition": changeStatusBool(ac['status']),
            "temperature": temperature
        }
    
    # ... Sisa logika Anda dari file asli ...
    terminal_status = get_status("terminal")
    tirai_status = get_status("tirai")
    door_status = get_status("door")
    plant_status = get_status("plant")
    valve_status = get_status("valve")
    auto_lamp_status = get_status("auto_lamp")
    auto_pump_status = get_status("auto_pump")
    
    conn.close()

    return {
        "message": "success in getting all device statuses",
        "lamp_one": lamp_status[0] if len(lamp_status) > 0 else None,
        "lamp_two": lamp_status[1] if len(lamp_status) > 1 else None,
        "lamp_three": lamp_status[2] if len(lamp_status) > 2 else None,
        "terminal": terminal_status,
        "tirai": tirai_status,
        "door": door_status,
        "plant": plant_status,
        "valve": valve_status,
        "sistem_lampu": auto_lamp_status,
        "sistem_tanaman": auto_pump_status,
        "fan_condition": fan_status.get("condition"),
        "fan_speed": fan_status.get("speed"),
        "ac_condition": ac_status.get("condition"),
        "ac_temperature": ac_status.get("temperature")
    }


# ... (SALIN SEMUA ENDPOINT GET/PUT ANDA YANG LAIN DI SINI, PASTIKAN PERBAIKI TYPO) ...
# Contoh perbaikan typo yang penting:
@app.put("/ac/condition")
async def set_ac_condition():
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM devices WHERE device_name = 'ac'")
    ac = cursor.fetchone()
    status = changeStatusBool(ac['status'])
    cursor.execute("UPDATE devices SET status = ? WHERE device_name = 'ac'", (not status,))
    conn.commit()
    conn.close()
    return {"message": "successfully switch ac"}

# ... (lanjutkan menyalin sisa endpoint Anda)

# Endpoint Chat
@app.post("/chat-simple")
async def ask_bot_simple(request: ChatRequest):
    # Logika chat Anda tidak perlu diubah
    result = subprocess.run(
        ["python3", "uji.py", request.chat],
        capture_output=True,
        text=True
    )
    # ... sisa logika chat Anda ...
    second_last_line = result.stdout.strip().split('\n')[-2]
    last_line = result.stdout.strip().split('\n')[-1]
    # ... dst
    return {
        "input": request.chat,
        "output": "some_output", # Ganti dengan variabel yang sesuai
        "response": "some_response" # Ganti dengan variabel yang sesuai
    }
