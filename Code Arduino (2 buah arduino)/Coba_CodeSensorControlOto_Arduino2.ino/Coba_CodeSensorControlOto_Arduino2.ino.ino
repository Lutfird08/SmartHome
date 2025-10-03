/*
  Kode Arduino 2 (Sensor Hub) yang dimodifikasi untuk integrasi
  - Menghilangkan semua delay() dan menggunakan millis() untuk penjadwalan.
  - Menggunakan variabel global untuk menyimpan data sensor dan status perangkat.
  - Menambahkan fungsi sendStatus() untuk melaporkan semua data dalam format CSV.
*/

#include <DHT.h>

// --- Definisi Pin dan Sensor ---
#define DHTPIN 2
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

const int pinLDR = A0;
const int LDR_Lampu = 45;
const int soilMoisturePin = A1;
const int Soil_Pump = 51;

// --- Variabel Global untuk Menyimpan Status dan Data ---
float currentTemperature = 0.0;
int currentLDRValue = 0;
int currentSoilMoisture = 0;
bool statusLampuLDR = false;
bool statusPompaTanah = false;

// --- Pengaturan Waktu (Non-Blocking) ---
unsigned long waktuSensorSebelumnya = 0;
const long intervalSensor = 2000; // Baca sensor setiap 2 detik

unsigned long waktuLaporanSebelumnya = 0;
const long intervalLaporan = 5000; // Kirim laporan setiap 5 detik

void setup() {
  Serial.begin(115200);
  dht.begin();

  pinMode(pinLDR, INPUT);
  pinMode(LDR_Lampu, OUTPUT);
  pinMode(soilMoisturePin, INPUT);
  pinMode(Soil_Pump, OUTPUT);

  // Set kondisi awal hardware
  digitalWrite(LDR_Lampu, LOW);
  digitalWrite(Soil_Pump, LOW);

  Serial.println("Arduino 2 (Sensor Hub) Siap.");
}

void loop() {
  unsigned long waktuSekarang = millis();

  // 1. Jadwalkan pembacaan sensor
  if (waktuSekarang - waktuSensorSebelumnya >= intervalSensor) {
    waktuSensorSebelumnya = waktuSekarang;
    readAllSensors();
    runAutomationLogic();
  }

  // 2. Jadwalkan pengiriman laporan status
  if (waktuSekarang - waktuLaporanSebelumnya >= intervalLaporan) {
    waktuLaporanSebelumnya = waktuSekarang;
    sendStatus();
  }
}

void readAllSensors() {
  // Baca semua sensor dan simpan di variabel global
  currentTemperature = dht.readTemperature();
  // Pastikan pembacaan suhu valid
  if (isnan(currentTemperature)) {
    Serial.println("Gagal membaca dari sensor DHT!");
    currentTemperature = 0; // Beri nilai default jika gagal
  }
  currentLDRValue = analogRead(pinLDR);
  currentSoilMoisture = analogRead(soilMoisturePin);
}

void runAutomationLogic() {
  // Logika untuk lampu berdasarkan LDR
  int ambangNyalaLDR = 890;
  statusLampuLDR = (currentLDRValue > ambangNyalaLDR);

  // Logika untuk pompa berdasarkan kelembapan tanah
  int batasTanahKering = 700;
  statusPompaTanah = (currentSoilMoisture > batasTanahKering);

  // Terapkan logika ke perangkat keras
  digitalWrite(LDR_Lampu, statusLampuLDR);
  digitalWrite(Soil_Pump, statusPompaTanah);
}

void sendStatus() {
  // Kirim semua data dalam satu baris format CSV
  // Format: suhu,nilai_ldr,nilai_kelembapan,status_lampu,status_pompa
  Serial.print(currentTemperature);
  Serial.print(",");
  Serial.print(currentLDRValue);
  Serial.print(",");
  Serial.print(currentSoilMoisture);
  Serial.print(",");
  Serial.print(statusLampuLDR ? "on" : "off");
  Serial.print(",");
  Serial.println(statusPompaTanah ? "on" : "off");
}