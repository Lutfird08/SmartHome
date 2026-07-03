#include "DHT.h"

#define NUM_BUTTONS 12

// =====================================================
// SERIAL CONFIG
// =====================================================
#define CMD_SERIAL   Serial2
#define DEBUG_SERIAL Serial

// =====================================================
// BUTTON INPUT
// =====================================================
const int buttonPins[NUM_BUTTONS] = {
  22, 24, 26, 28, 30, 32,
  34, 36, 38, 40, 42, 44
};

// =====================================================
// OUTPUT CONTROL
// =====================================================
const int outputPins[NUM_BUTTONS] = {
  49, 51, 33, 37, 31, 31,
  31, 47, 35, 45, 31, 31
};

// =====================================================
// AC RELAY PIN
// =====================================================
#define AC_UP_PIN     39
#define AC_DOWN_PIN   41
#define AC_POWER_PIN  43

const unsigned long acPulseDuration = 500;

// =====================================================
// L298N
// =====================================================
const int l298nPins[] = {
  7, 6, 5,
  4, 3, 2
};

// =====================================================
// SENSOR
// =====================================================
byte pinLDR  = A0;
byte pinSoil = A1;

// =====================================================
// DHT11
// =====================================================
#define DHTPIN 14
#define DHTTYPE DHT11

DHT dht(DHTPIN, DHTTYPE);

// =====================================================
// BUTTON NAMES
// =====================================================
const char* buttonNames[NUM_BUTTONS] = {
  "lampu_utama",
  "lampu_kamar",
  "lampu_tamu",
  "colokan_terminal",
  "tirai_tutup",
  "tirai_buka",
  "kipas",
  "pompa_penyiram",
  "solenoid_valve",
  "solenoid_door",
  "otomatis_pompa",
  "otomatis_lampu"
};

// =====================================================
// BUTTON VARIABLES
// =====================================================
bool buttonState[NUM_BUTTONS];
bool lastButtonState[NUM_BUTTONS];
bool toggleState[NUM_BUTTONS];

unsigned long lastDebounceTime[NUM_BUTTONS];
const unsigned long debounceDelay = 50;

// =====================================================
// SOLENOID
// =====================================================
const int SOLENOID_DOOR_INDEX = 9;

unsigned long solenoidStartTime = 0;
bool solenoidActive = false;

const unsigned long solenoidDuration = 5000;

// =====================================================
// SENSOR CACHE
// =====================================================
int lastLDR = -1;
int lastSoil = -1;

float lastTemp = -999;
float lastHum  = -999;

unsigned long lastSensorSend = 0;
const unsigned long sensorInterval = 10000;

// =====================================================
// TIRAI STATE
// =====================================================
bool tiraiBukaState  = false;
bool tiraiTutupState = false;

// Durasi gerak tirai — 200ms lalu otomatis stop
bool tiraiSerialActive = false;
unsigned long tiraiSerialStart = 0;
const unsigned long tiraiSerialDuration = 200;

// Durasi gerak tirai dari tombol fisik — sama 200ms
bool tiraiButtonActive = false;
unsigned long tiraiButtonStart = 0;
const unsigned long tiraiButtonDuration = 200;

// =====================================================
// AC PULSE TIMER
// =====================================================
bool acUpActive = false;
bool acDownActive = false;
bool acPowerActive = false;

unsigned long acUpStart = 0;
unsigned long acDownStart = 0;
unsigned long acPowerStart = 0;

// =====================================================
// SETUP
// =====================================================
void setup() {

  DEBUG_SERIAL.begin(115200);
  CMD_SERIAL.begin(115200);

  dht.begin();

  for (int i = 0; i < NUM_BUTTONS; i++) {

    pinMode(buttonPins[i], INPUT_PULLUP);

    if (outputPins[i] != 31) {
      pinMode(outputPins[i], OUTPUT);
      digitalWrite(outputPins[i], HIGH);
    }

    buttonState[i] = HIGH;
    lastButtonState[i] = HIGH;
    toggleState[i] = false;
  }

  pinMode(AC_UP_PIN, OUTPUT);
  pinMode(AC_DOWN_PIN, OUTPUT);
  pinMode(AC_POWER_PIN, OUTPUT);

  digitalWrite(AC_UP_PIN, HIGH);
  digitalWrite(AC_DOWN_PIN, HIGH);
  digitalWrite(AC_POWER_PIN, HIGH);

  for (int i = 0; i < 6; i++) {
    pinMode(l298nPins[i], OUTPUT);
    digitalWrite(l298nPins[i], LOW);
  }

  DEBUG_SERIAL.println("SYSTEM READY");
  CMD_SERIAL.println("SYSTEM_READY");
}

// =====================================================
// LOOP
// =====================================================
void loop() {

  // ==========================================
  // SERIAL COMMAND
  // ==========================================
  if (CMD_SERIAL.available()) {
    processSerialCommand();
  }

  // ==========================================
  // SENSOR SEND
  // ==========================================
  if (millis() - lastSensorSend >= sensorInterval) {
    lastSensorSend = millis();
    sendSensorData();
  }

  // ==========================================
  // BUTTON CHECK
  // ==========================================
  for (int i = 0; i < NUM_BUTTONS; i++) {

    int reading = digitalRead(buttonPins[i]);

    if (reading != lastButtonState[i]) {
      lastDebounceTime[i] = millis();
    }

    if ((millis() - lastDebounceTime[i]) > debounceDelay) {
      if (reading != buttonState[i]) {
        buttonState[i] = reading;
        if (buttonState[i] == LOW) {
          handleButton(i);
        }
      }
    }

    lastButtonState[i] = reading;
  }

  // ==========================================
  // TIRAI — tombol fisik gerak 200ms lalu stop
  // ==========================================
  bool tutupPressed = digitalRead(buttonPins[4]) == LOW;
  bool bukaPressed  = digitalRead(buttonPins[5]) == LOW;

  if (tutupPressed && !tiraiButtonActive && !tiraiSerialActive) {
    // Mulai pulse tutup dari tombol fisik
    tiraiButtonActive = true;
    tiraiButtonStart  = millis();
    tiraiTutupState   = true;
    tiraiBukaState    = false;
    tutupTirai(45);
    CMD_SERIAL.println("tirai:TUTUP");

  } else if (bukaPressed && !tiraiButtonActive && !tiraiSerialActive) {
    // Mulai pulse buka dari tombol fisik
    tiraiButtonActive = true;
    tiraiButtonStart  = millis();
    tiraiBukaState    = true;
    tiraiTutupState   = false;
    bukaTirai(45);
    CMD_SERIAL.println("tirai:BUKA");

  } else if (tiraiButtonActive) {
    // Tombol sedang aktif — cek apakah 200ms sudah lewat
    if (millis() - tiraiButtonStart >= tiraiButtonDuration) {
      offTirai();
      tiraiButtonActive = false;
      tiraiBukaState    = false;
      tiraiTutupState   = false;
      CMD_SERIAL.println("tirai:OFF");
    }

  } else if (tiraiSerialActive) {
    // Perintah dari serial sedang aktif — cek 200ms
    if (millis() - tiraiSerialStart >= tiraiSerialDuration) {
      offTirai();
      tiraiSerialActive = false;
      tiraiBukaState    = false;
      tiraiTutupState   = false;
      CMD_SERIAL.println("tirai:OFF");
    }

  } else {
    // Tidak ada perintah apapun — pastikan motor mati
    if (tiraiBukaState || tiraiTutupState) {
      offTirai();
      CMD_SERIAL.println("tirai:OFF");
      tiraiBukaState  = false;
      tiraiTutupState = false;
    }
  }

  // ==========================================
  // SOLENOID TIMER
  // ==========================================
  if (solenoidActive &&
      millis() - solenoidStartTime >= solenoidDuration) {

    digitalWrite(outputPins[SOLENOID_DOOR_INDEX], HIGH);
    solenoidActive = false;
    CMD_SERIAL.println("solenoid_door:OFF");
  }

  // ==========================================
  // AC AUTO OFF TIMER
  // ==========================================
  handleACPulse();
}

// =====================================================
// HANDLE BUTTON
// =====================================================
void handleButton(int index) {

  if (index == SOLENOID_DOOR_INDEX) {
    if (!solenoidActive) {
      solenoidActive = true;
      solenoidStartTime = millis();
      digitalWrite(outputPins[index], LOW);
      CMD_SERIAL.println("solenoid_door:ON");
    }
    return;
  }

  // Tirai ditangani di loop utama, skip di sini
  if (index == 4 || index == 5) return;

  toggleState[index] = !toggleState[index];

  if (outputPins[index] != 31) {
    digitalWrite(outputPins[index], toggleState[index] ? LOW : HIGH);
  }

  CMD_SERIAL.print(buttonNames[index]);
  CMD_SERIAL.print(":");
  CMD_SERIAL.println(toggleState[index] ? "ON" : "OFF");

  if (index == 6) {
    if (toggleState[6]) onKipas(50);
    else offKipas();
  }
}

// =====================================================
// SENSOR DATA
// =====================================================
void sendSensorData() {

  int nilaiLDR  = analogRead(pinLDR);
  int nilaiSoil = analogRead(pinSoil);

  float hum  = dht.readHumidity();
  float temp = dht.readTemperature();

  if (abs(nilaiLDR - lastLDR) > 5) {
    CMD_SERIAL.print("ldr:");
    CMD_SERIAL.println(nilaiLDR);
    lastLDR = nilaiLDR;
  }

  if (abs(nilaiSoil - lastSoil) > 5) {
    CMD_SERIAL.print("soil:");
    CMD_SERIAL.println(nilaiSoil);
    lastSoil = nilaiSoil;
  }

  if (!isnan(hum) && !isnan(temp)) {
    if (abs(hum - lastHum) > 1) {
      CMD_SERIAL.print("humidity:");
      CMD_SERIAL.println(hum);
      lastHum = hum;
    }
    if (abs(temp - lastTemp) > 0.5) {
      CMD_SERIAL.print("temperature:");
      CMD_SERIAL.println(temp);
      lastTemp = temp;
    }
  }
}

// =====================================================
// SERIAL COMMAND
// =====================================================
void processSerialCommand() {

  String command = CMD_SERIAL.readStringUntil('\n');
  command.trim();
  if (command.length() == 0) return;

  DEBUG_SERIAL.print("CMD: ");
  DEBUG_SERIAL.println(command);

  // PING
  if (command == "PING") {
    CMD_SERIAL.println("ARDUINO:ALIVE");
  }

  // STATUS
  else if (command == "STATUS") {
    for (int i = 0; i < NUM_BUTTONS; i++) {
      if (outputPins[i] != 31) {
        CMD_SERIAL.print(buttonNames[i]);
        CMD_SERIAL.print(":");
        CMD_SERIAL.println(toggleState[i] ? "ON" : "OFF");
      }
    }
  }

  // ON
  else if (command.startsWith("ON ")) {
    int index = command.substring(3).toInt();
    if (index >= 0 && index < NUM_BUTTONS) {
      toggleState[index] = true;
      if (outputPins[index] != 31) digitalWrite(outputPins[index], LOW);
      CMD_SERIAL.print(buttonNames[index]);
      CMD_SERIAL.println(":ON");
      if (index == 6) onKipas(50);
    }
  }

  // OFF
  else if (command.startsWith("OFF ")) {
    int index = command.substring(4).toInt();
    if (index >= 0 && index < NUM_BUTTONS) {
      toggleState[index] = false;
      if (outputPins[index] != 31) digitalWrite(outputPins[index], HIGH);
      CMD_SERIAL.print(buttonNames[index]);
      CMD_SERIAL.println(":OFF");
      if (index == 6) offKipas();
    }
  }

  // AC POWER
  else if (command == "AC_POWER") {
    triggerACPower();
    CMD_SERIAL.println("ac_power:PULSE");
  }

  // AC UP
  else if (command == "AC_UP") {
    triggerACUp();
    CMD_SERIAL.println("ac_up:PULSE");
  }

  // AC DOWN
  else if (command == "AC_DOWN") {
    triggerACDown();
    CMD_SERIAL.println("ac_down:PULSE");
  }

  // KIPAS ON
  else if (command.startsWith("KIPASON ")) {
    int speed = command.substring(8).toInt();
    onKipas(speed);
    CMD_SERIAL.println("kipas:ON");
  }

  // KIPAS OFF
  else if (command == "KIPASOFF") {
    offKipas();
    CMD_SERIAL.println("kipas:OFF");
  }

  // TIRAI BUKA
  else if (command.startsWith("TIRAIBUKA ")) {
    int speed = command.substring(10).toInt();
    bukaTirai(speed);
    tiraiSerialActive = true;
    tiraiSerialStart  = millis();
    tiraiBukaState    = true;
    tiraiTutupState   = false;
    CMD_SERIAL.println("tirai:BUKA");
  }

  // TIRAI TUTUP
  else if (command.startsWith("TIRAITUTUP ")) {
    int speed = command.substring(11).toInt();
    tutupTirai(speed);
    tiraiSerialActive = true;
    tiraiSerialStart  = millis();
    tiraiTutupState   = true;
    tiraiBukaState    = false;
    CMD_SERIAL.println("tirai:TUTUP");
  }

  // TIRAI STOP
  else if (command == "TIRAIOFF") {
    offTirai();
    tiraiSerialActive = false;
    tiraiBukaState    = false;
    tiraiTutupState   = false;
    CMD_SERIAL.println("tirai:OFF");
  }
}

// =====================================================
// AC CONTROL
// =====================================================
void triggerACPower() {
  digitalWrite(AC_POWER_PIN, LOW);
  acPowerActive = true;
  acPowerStart  = millis();
}

void triggerACUp() {
  digitalWrite(AC_UP_PIN, LOW);
  acUpActive = true;
  acUpStart  = millis();
}

void triggerACDown() {
  digitalWrite(AC_DOWN_PIN, LOW);
  acDownActive = true;
  acDownStart  = millis();
}

void handleACPulse() {
  if (acPowerActive && millis() - acPowerStart >= acPulseDuration) {
    digitalWrite(AC_POWER_PIN, HIGH);
    acPowerActive = false;
  }
  if (acUpActive && millis() - acUpStart >= acPulseDuration) {
    digitalWrite(AC_UP_PIN, HIGH);
    acUpActive = false;
  }
  if (acDownActive && millis() - acDownStart >= acPulseDuration) {
    digitalWrite(AC_DOWN_PIN, HIGH);
    acDownActive = false;
  }
}

// =====================================================
// TIRAI
// =====================================================
void tutupTirai(int speed) {
  analogWrite(l298nPins[0], speed);
  digitalWrite(l298nPins[1], LOW);
  digitalWrite(l298nPins[2], HIGH);
}

void bukaTirai(int speed) {
  analogWrite(l298nPins[0], speed);
  digitalWrite(l298nPins[1], HIGH);
  digitalWrite(l298nPins[2], LOW);
}

void offTirai() {
  analogWrite(l298nPins[0], 0);
  digitalWrite(l298nPins[1], LOW);
  digitalWrite(l298nPins[2], LOW);
}

// =====================================================
// KIPAS
// =====================================================
void onKipas(int speed) {
  analogWrite(l298nPins[5], speed);
  digitalWrite(l298nPins[4], HIGH);
  digitalWrite(l298nPins[3], LOW);
}

void offKipas() {
  analogWrite(l298nPins[5], 0);
  digitalWrite(l298nPins[4], LOW);
  digitalWrite(l298nPins[3], LOW);
}
