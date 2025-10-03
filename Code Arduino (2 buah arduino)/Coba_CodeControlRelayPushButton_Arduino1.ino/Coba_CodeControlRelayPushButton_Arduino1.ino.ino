/*
  Kode Arduino 1 yang dimodifikasi untuk integrasi dengan FastAPI
  - Menambahkan variabel global untuk melacak status semua perangkat.
  - Logika kontrol diperbarui untuk mengubah variabel status.
  - Menambahkan fungsi sendStatus() untuk melaporkan semua status ke serial
    secara periodik dengan format CSV.
*/

// --- Variabel untuk melacak status perangkat ---
bool statusLampuUtama = false;
bool statusLampuKamar = false;
bool statusLampuTamu = false;
bool statusWaterPump = false;
bool statusTerminal = false;
bool statusPintu = false; // Solenoid_DoorLock
bool statusValve = false;  // Solenoid_Valve
bool statusOtoLamp = false;
bool statusOtoPump = false;
bool statusTirai = false; // Menyimpan status terakhir tirai (on/off)
bool statusAC = false;    // Menyimpan status terakhir AC (on/off)
int kecepatanKipas = 0; // 0=mati, 1, 2, 3

String command;

// --- Definisi Pin Perangkat (dari kode Anda) ---
const int AC_Up_button = 41;
const int AC_Down_button = 39;
const int AC_OnOff_button = 37;
const int Solenoid_DoorLock = 35;
const int Solenoid_Valve = 33;
const int Lamp_Utama = 31;
const int Lamp_Kamar = 29;
const int Lamp_Tamu = 27;
const int WaterPump = 25;
const int Terminal = 43;

// --- Definisi Pin Tombol (dari kode Anda) ---
const int Button_Lamp_Utama = 30;
const int Button_Lamp_Kamar = 28;
const int Button_Lamp_Tamu = 26;
const int Button_WaterPump = 24;
const int Button_Terminal = 42;
const int Button_Solenoid_DoorLock = 34;
const int Button_Solenoid_Valve = 32;
const int Button_Oto_Lamp = 46;
const int Button_Oto_Pump = 48;
const int Button_TiraiMati = 38;
const int Button_TiraiHidup = 40;
const int Fan_Button = 36;

// --- Definisi Pin Motor (dari kode Anda) ---
const int ENA = 7;
const int IN1 = 6;
const int IN2 = 5;
const int IN3 = 4;
const int IN4 = 3;
const int ENB = 2;

const int Oto_Lamp = 47;
const int Oto_Pump = 49;

// --- Pengaturan Waktu untuk Laporan Status ---
unsigned long waktuSebelumnya = 0;
const long intervalKirim = 5000; // Kirim status setiap 5 detik

void setup() {
  Serial.begin(115200); // Menggunakan baud rate dari kode Anda

  // Inisialisasi pin output
  pinMode(AC_Up_button, OUTPUT);
  pinMode(AC_Down_button, OUTPUT);
  pinMode(AC_OnOff_button, OUTPUT);
  pinMode(Solenoid_DoorLock, OUTPUT);
  pinMode(Solenoid_Valve, OUTPUT);
  pinMode(Lamp_Utama, OUTPUT);
  pinMode(Lamp_Kamar, OUTPUT);
  pinMode(Lamp_Tamu, OUTPUT);
  pinMode(WaterPump, OUTPUT);
  pinMode(Terminal, OUTPUT);
  pinMode(ENA, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(ENB, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
  pinMode(Oto_Lamp, OUTPUT);
  pinMode(Oto_Pump, OUTPUT);

  // Inisialisasi pin input
  pinMode(Button_Lamp_Utama, INPUT_PULLUP);
  pinMode(Button_Lamp_Kamar, INPUT_PULLUP);
  pinMode(Button_Lamp_Tamu, INPUT_PULLUP);
  pinMode(Button_WaterPump, INPUT_PULLUP);
  pinMode(Button_Terminal, INPUT_PULLUP);
  pinMode(Button_Solenoid_DoorLock, INPUT_PULLUP);
  pinMode(Button_Solenoid_Valve, INPUT_PULLUP);
  pinMode(Button_TiraiHidup, INPUT_PULLUP);
  pinMode(Button_TiraiMati, INPUT_PULLUP);
  pinMode(Fan_Button, INPUT_PULLUP);
  pinMode(Button_Oto_Lamp, INPUT_PULLUP);
  pinMode(Button_Oto_Pump, INPUT_PULLUP);

  updateAllHardware(); // Set semua hardware ke status awal
  Serial.println("Arduino 1 Siap.");
}

void loop() {
  // 1. Cek semua tombol fisik
  checkAllButtons();

  // 2. Cek perintah dari serial
  if (Serial.available()) {
    processSerialCommand();
  }

  // 3. Kirim laporan status secara periodik
  unsigned long waktuSekarang = millis();
  if (waktuSekarang - waktuSebelumnya >= intervalKirim) {
    waktuSebelumnya = waktuSekarang;
    sendStatus();
  }
}

void checkAllButtons() {
  // Toggle status jika tombol ditekan
  if (digitalRead(Button_Lamp_Utama) == LOW) { statusLampuUtama = !statusLampuUtama; delay(200); }
  if (digitalRead(Button_Lamp_Kamar) == LOW) { statusLampuKamar = !statusLampuKamar; delay(200); }
  if (digitalRead(Button_Lamp_Tamu) == LOW) { statusLampuTamu = !statusLampuTamu; delay(200); }
  if (digitalRead(Button_WaterPump) == LOW) { statusWaterPump = !statusWaterPump; delay(200); }
  if (digitalRead(Button_Terminal) == LOW) { statusTerminal = !statusTerminal; delay(200); }
  if (digitalRead(Button_Solenoid_DoorLock) == LOW) { statusPintu = !statusPintu; delay(200); }
  if (digitalRead(Button_Solenoid_Valve) == LOW) { statusValve = !statusValve; delay(200); }
  if (digitalRead(Button_Oto_Lamp) == LOW) { statusOtoLamp = !statusOtoLamp; delay(200); }
  if (digitalRead(Button_Oto_Pump) == LOW) { statusOtoPump = !statusOtoPump; delay(200); }
  
  if (digitalRead(Button_TiraiMati) == LOW) { 
      statusTirai = false; // Set status tirai mati
      // Jalankan motor
      digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
      analogWrite(ENA, 73); delay(152);
      digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
  }
  if (digitalRead(Button_TiraiHidup) == LOW) { 
      statusTirai = true; // Set status tirai hidup
      // Jalankan motor
      digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);
      analogWrite(ENA, 55); delay(117);
      digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
  }

  if (digitalRead(Fan_Button) == LOW) {
    kecepatanKipas = (kecepatanKipas + 1) % 4; // 0, 1, 2, 3
    delay(250);
  }

  updateAllHardware(); // Terapkan perubahan status ke hardware
}

void processSerialCommand() {
  command = Serial.readStringUntil('\n');
  command.trim();

  // Lampu
  if (command.equals("lampu1_hidup")) { statusLampuUtama = true; }
  else if (command.equals("lampu1_mati")) { statusLampuUtama = false; }
  else if (command.equals("lampu2_hidup")) { statusLampuKamar = true; }
  else if (command.equals("lampu2_mati")) { statusLampuKamar = false; }
  else if (command.equals("lampu3_hidup")) { statusLampuTamu = true; }
  else if (command.equals("lampu3_mati")) { statusLampuTamu = false; }
  else if (command.equals("lampusemua_hidup")) { statusLampuUtama = true; statusLampuKamar = true; statusLampuTamu = true; }
  else if (command.equals("lampusemua_mati")) { statusLampuUtama = false; statusLampuKamar = false; statusLampuTamu = false; }

  // Perangkat lain
  else if (command.equals("kunci_hidup")) { statusPintu = true; }
  else if (command.equals("kunci_mati")) { statusPintu = false; }
  else if (command.equals("kran_hidup")) { statusValve = true; }
  else if (command.equals("kran_mati")) { statusValve = false; }
  else if (command.equals("pompa_hidup")) { statusWaterPump = true; statusValve = true; }
  else if (command.equals("pompa_mati")) { statusWaterPump = false; statusValve = false; }
  else if (command.equals("terminal_hidup")) { statusTerminal = true; }
  else if (command.equals("terminal_mati")) { statusTerminal = false; }

  // Sistem Otomatis
  else if (command.equals("otolampu_hidup")) { statusOtoLamp = true; }
  else if (command.equals("otolampu_mati")) { statusOtoLamp = false; }
  else if (command.equals("otopompa_hidup")) { statusOtoPump = true; }
  else if (command.equals("otopompa_mati")) { statusOtoPump = false; }
  
  // Perintah Aksi (tidak mengubah status permanen, hanya menjalankan aksi)
  else if (command.equals("ac_hidup")) { statusAC = true; digitalWrite(AC_OnOff_button, HIGH); delay(200); digitalWrite(AC_OnOff_button,LOW); }
  else if (command.equals("ac_mati")) { statusAC = false; digitalWrite(AC_OnOff_button, HIGH); delay(200); digitalWrite(AC_OnOff_button,LOW); }
  else if (command.equals("ac_naik")) { digitalWrite(AC_Up_button, HIGH); delay(200); digitalWrite(AC_Up_button,LOW); }
  else if (command.equals("ac_turun")) { digitalWrite(AC_Down_button, HIGH); delay(200); digitalWrite(AC_Down_button,LOW); }
  else if (command.equals("kipas_1")) { kecepatanKipas = 1;}
  else if (command.equals("kipas_2")) { kecepatanKipas = 2;}
  else if (command.equals("kipas_3")) { kecepatanKipas = 3;}
  else if (command.equals("kipas_mati")) { kecepatanKipas = 0; }
  else if (command.equals("tirai_hidup")) { statusTirai = true; /* Jalankan motor */ digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH); analogWrite(ENA, 55); delay(117); digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);}
  else if (command.equals("tirai_mati")) { statusTirai = false; /* Jalankan motor */ digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW); analogWrite(ENA, 73); delay(152); digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);}

  updateAllHardware(); // Terapkan perubahan ke hardware
}

void updateAllHardware() {
  // Terapkan semua status variabel ke pin fisik
  digitalWrite(Lamp_Utama, statusLampuUtama);
  digitalWrite(Lamp_Kamar, statusLampuKamar);
  digitalWrite(Lamp_Tamu, statusLampuTamu);
  digitalWrite(WaterPump, statusWaterPump);
  digitalWrite(Terminal, statusTerminal);
  digitalWrite(Solenoid_DoorLock, !statusPintu); // Logika terbalik untuk kunci? sesuaikan jika perlu
  digitalWrite(Solenoid_Valve, statusValve);
  digitalWrite(Oto_Lamp, statusOtoLamp);
  digitalWrite(Oto_Pump, statusOtoPump);
  
  // Update Kipas
  switch (kecepatanKipas) {
    case 0: digitalWrite(IN3, LOW); digitalWrite(IN4, LOW); break;
    case 1: digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH); analogWrite(ENB, 80); break;
    case 2: digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH); analogWrite(ENB, 100); break;
    case 3: digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH); analogWrite(ENB, 60); break;
  }
}

// Fungsi untuk mengirim laporan status dalam format CSV
void sendStatus() {
  // Format CSV: lamp1,lamp2,lamp3,terminal,tirai,pintu,pompa,valve,sistem_lampu,sistem_pompa,fan_on,fan_speed,ac_on
  Serial.print(statusLampuUtama ? "on" : "off"); Serial.print(",");
  Serial.print(statusLampuKamar ? "on" : "off"); Serial.print(",");
  Serial.print(statusLampuTamu ? "on" : "off"); Serial.print(",");
  Serial.print(statusTerminal ? "on" : "off"); Serial.print(",");
  Serial.print(statusTirai ? "on" : "off"); Serial.print(",");
  Serial.print(statusPintu ? "on" : "off"); Serial.print(",");
  Serial.print(statusWaterPump ? "on" : "off"); Serial.print(",");
  Serial.print(statusValve ? "on" : "off"); Serial.print(",");
  Serial.print(statusOtoLamp ? "on" : "off"); Serial.print(",");
  Serial.print(statusOtoPump ? "on" : "off"); Serial.print(",");
  Serial.print(kecepatanKipas > 0 ? "on" : "off"); Serial.print(",");
  Serial.print(kecepatanKipas); Serial.print(",");
  Serial.println(statusAC ? "on" : "off");
}