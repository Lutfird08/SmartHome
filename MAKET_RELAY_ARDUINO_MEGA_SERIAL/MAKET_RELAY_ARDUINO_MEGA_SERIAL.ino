#include "DHT.h"

#define NUM_BUTTONS 12

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
// KIPAS STATE (4 State)
// =====================================================
int fanSpeedState = 0; // 0=OFF, 1=80, 2=100, 3=60

// =====================================================
// SENSOR CACHE
// =====================================================
int lastLDR = -1;
int lastSoil = -1;
float lastTemp = -999;
float lastHum  = -999;

unsigned long lastSensorSend = 0;
// DIPERCEPAT MENJADI 1 DETIK AGAR PYTHON TIDAK TIMEOUT
const unsigned long sensorInterval = 1000; 

// =====================================================
// TIRAI STATE
// =====================================================
bool tiraiBukaState  = false;
bool tiraiTutupState = false;

const unsigned long tiraiTutupDuration = 152;
const unsigned long tiraiBukaDuration = 117;
unsigned long currentTiraiDuration = 200;

bool tiraiSerialActive = false;
unsigned long tiraiSerialStart = 0;

bool tiraiButtonActive = false;
unsigned long tiraiButtonStart = 0;

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
// FUNGSI BROADCAST (DUAL CHANNEL)
// =====================================================
// Fungsi ini mengirim pesan ke Laptop (Serial) dan ESP32 (Serial2) bersamaan
void broadcast(String msg) {
  Serial.println(msg);
  Serial2.println(msg);
}

// =====================================================
// SETUP
// =====================================================
void setup() {
  // Nyalakan kedua telinga (Jalur komunikasi)
  Serial.begin(115200);   // Untuk Kabel USB (Python Laptop)
  Serial2.begin(115200);  // Untuk ESP32 (Web/WiFi)

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

  broadcast("SYSTEM_READY");
}

// =====================================================
// LOOP
// =====================================================
void loop() {

  // ==========================================
  // DUAL SERIAL CHECK (Baca perintah dari 2 sumber)
  // ==========================================
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.length() > 0) executeCommand(cmd);
  }
  
  if (Serial2.available()) {
    String cmd = Serial2.readStringUntil('\n');
    cmd.trim();
    if (cmd.length() > 0) executeCommand(cmd);
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
  // TIRAI FISIK
  // ==========================================
  bool tutupPressed = digitalRead(buttonPins[4]) == LOW;
  bool bukaPressed  = digitalRead(buttonPins[5]) == LOW;

  if (tutupPressed && !tiraiButtonActive && !tiraiSerialActive) {
    tiraiButtonActive = true;
    tiraiButtonStart  = millis();
    tiraiTutupState   = true;
    tiraiBukaState    = false;
    currentTiraiDuration = tiraiTutupDuration; 
    tutupTirai(73); 
    broadcast("tirai:TUTUP");

  } else if (bukaPressed && !tiraiButtonActive && !tiraiSerialActive) {
    tiraiButtonActive = true;
    tiraiButtonStart  = millis();
    tiraiBukaState    = true;
    tiraiTutupState   = false;
    currentTiraiDuration = tiraiBukaDuration; 
    bukaTirai(55); 
    broadcast("tirai:BUKA");

  } else if (tiraiButtonActive) {
    if (millis() - tiraiButtonStart >= currentTiraiDuration) {
      offTirai();
      tiraiButtonActive = false;
      tiraiBukaState    = false;
      tiraiTutupState   = false;
      broadcast("tirai:OFF");
    }

  } else if (tiraiSerialActive) {
    if (millis() - tiraiSerialStart >= currentTiraiDuration) {
      offTirai();
      tiraiSerialActive = false;
      tiraiBukaState    = false;
      tiraiTutupState   = false;
      broadcast("tirai:OFF");
    }

  } else {
    if (tiraiBukaState || tiraiTutupState) {
      offTirai();
      broadcast("tirai:OFF");
      tiraiBukaState  = false;
      tiraiTutupState = false;
    }
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
  if (index == 4 || index == 5) return;

  if (index == 6) {
    fanSpeedState = (fanSpeedState + 1) % 4; 
    toggleState[6] = (fanSpeedState != 0);   
    
    if (fanSpeedState == 0) {
      offKipas();
      broadcast("kipas:OFF");
    } else {
      int pwm = (fanSpeedState == 1) ? 80 : (fanSpeedState == 2) ? 100 : 60;
      onKipas(pwm);
      broadcast("kipas:ON");
    }
    return; 
  }

  toggleState[index] = !toggleState[index];
  if (outputPins[index] != 31) {
    digitalWrite(outputPins[index], toggleState[index] ? LOW : HIGH);
  }
  broadcast(String(buttonNames[index]) + ":" + (toggleState[index] ? "ON" : "OFF"));
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
    broadcast("ldr:" + String(nilaiLDR));
    lastLDR = nilaiLDR;
  }

  if (abs(nilaiSoil - lastSoil) > 5) {
    broadcast("soil:" + String(nilaiSoil));
    lastSoil = nilaiSoil;
  }

  if (!isnan(hum) && !isnan(temp)) {
    if (abs(hum - lastHum) > 1) {
      broadcast("humidity:" + String(hum));
      lastHum = hum;
    }
    if (abs(temp - lastTemp) > 0.5) {
      broadcast("temperature:" + String(temp));
      lastTemp = temp;
    }
  }
}

// =====================================================
// EXECUTE COMMAND (LOGIKA UTAMA)
// =====================================================
void executeCommand(String command) {
  if (command == "PING") {
    broadcast("ARDUINO:ALIVE");
  }

  else if (command == "STATUS") {
    for (int i = 0; i < NUM_BUTTONS; i++) {
      if (outputPins[i] != 31) {
        broadcast(String(buttonNames[i]) + ":" + (toggleState[i] ? "ON" : "OFF"));
      }
    }
  }

  else if (command.startsWith("ON ")) {
    int index = command.substring(3).toInt();
    if (index >= 0 && index < NUM_BUTTONS) {
      toggleState[index] = true;
      if (outputPins[index] != 31) digitalWrite(outputPins[index], LOW);
      broadcast(String(buttonNames[index]) + ":ON");
      
      if (index == 6) {
        fanSpeedState = 1;
        onKipas(80);
      }
    }
  }

  else if (command.startsWith("OFF ")) {
    int index = command.substring(4).toInt();
    if (index >= 0 && index < NUM_BUTTONS) {
      toggleState[index] = false;
      if (outputPins[index] != 31) digitalWrite(outputPins[index], HIGH);
      broadcast(String(buttonNames[index]) + ":OFF");
      
      if (index == 6) {
        fanSpeedState = 0;
        offKipas();
      }
    }
  }

  else if (command == "AC_POWER") {
    triggerACPower();
    broadcast("ac_power:PULSE");
  }

  else if (command == "AC_UP") {
    triggerACUp();
    broadcast("ac_up:PULSE");
  }

  else if (command == "AC_DOWN") {
    triggerACDown();
    broadcast("ac_down:PULSE");
  }

  else if (command.startsWith("KIPASON ")) {
    int speed = command.substring(8).toInt(); 
    if (speed == 80) fanSpeedState = 1;
    else if (speed == 100) fanSpeedState = 2;
    else if (speed == 60) fanSpeedState = 3;
    else { fanSpeedState = 1; speed = 80; }

    toggleState[6] = true;
    onKipas(speed);
    broadcast("kipas:ON");
  }

  else if (command == "KIPASOFF") {
    offKipas();
    toggleState[6] = false;
    fanSpeedState = 0;
    broadcast("kipas:OFF");
  }

  else if (command.startsWith("TIRAIBUKA ")) {
    bukaTirai(55); 
    tiraiSerialActive = true;
    tiraiSerialStart  = millis();
    tiraiBukaState    = true;
    tiraiTutupState   = false;
    currentTiraiDuration = tiraiBukaDuration; 
    broadcast("tirai:BUKA");
  }

  else if (command.startsWith("TIRAITUTUP ")) {
    tutupTirai(73); 
    tiraiSerialActive = true;
    tiraiSerialStart  = millis();
    tiraiTutupState   = true;
    tiraiBukaState    = false;
    currentTiraiDuration = tiraiTutupDuration; 
    broadcast("tirai:TUTUP");
  }

  else if (command == "TIRAIOFF") {
    offTirai();
    tiraiSerialActive = false;
    tiraiBukaState    = false;
    tiraiTutupState   = false;
    broadcast("tirai:OFF");
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
