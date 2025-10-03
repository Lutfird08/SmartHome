String command;

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

// Add these constants for push buttons
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

const int ENA = 7;  
const int IN1 = 6;   
const int IN2 = 5;   
const int IN3 = 4;   
const int IN4 = 3;   
const int ENB = 2; 

const int Oto_Lamp = 47;
const int Oto_Pump = 49;

// Variabel untuk status tombol kontrol tirai (default: HIGH = tidak ditekan)
bool tiraiMatiButtonState = HIGH;
bool tiraiHidupButtonState = HIGH;

// Variabel untuk status tombol kontrol kipas dan variabel untuk menyimpan kecepatan kipas
bool fanButtonState = HIGH;
int fanSpeed = 0; 

// fungsiuntuk check PushButton
void checkPushButton(int buttonPin, int devicePin);

void setup() {
  Serial.begin(115200);
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
  
}

void loop() {
  checkPushButton(Button_Lamp_Utama, Lamp_Utama);
  checkPushButton(Button_Lamp_Kamar, Lamp_Kamar);
  checkPushButton(Button_Lamp_Tamu, Lamp_Tamu);
  checkPushButton(Button_WaterPump, WaterPump);
  checkPushButton(Button_Terminal, Terminal);
  checkPushButton(Button_Solenoid_DoorLock, Solenoid_DoorLock);
  checkPushButton(Button_Solenoid_Valve, Solenoid_Valve);
  checkPushButton(Button_Oto_Lamp, Oto_Lamp);
  checkPushButton(Button_Oto_Pump, Oto_Pump);
  

// Check push button for "tirai_mati"
  if (digitalRead(Button_TiraiMati) == LOW && tiraiMatiButtonState == HIGH) {
    digitalWrite(IN1, HIGH);
    digitalWrite(IN2, LOW);
    analogWrite(ENA, 73);
    delay(152);
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, LOW);
    tiraiMatiButtonState = LOW;
  } else if (digitalRead(Button_TiraiMati) == HIGH) {
    tiraiMatiButtonState = HIGH;
  }

  // Check push button for "tirai_hidup"
  if (digitalRead(Button_TiraiHidup) == LOW && tiraiHidupButtonState == HIGH) {
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, HIGH);
    analogWrite(ENA, 55);
    delay(117);
    digitalWrite(IN1, LOW);
    digitalWrite(IN2, LOW);
    tiraiHidupButtonState = LOW;
  } else if (digitalRead(Button_TiraiHidup) == HIGH) {
    tiraiHidupButtonState = HIGH;
  }
  
  // Check push button for "kipas"
  if (digitalRead(Fan_Button) == LOW && fanButtonState == HIGH) {
    // Button has been pressed
    fanSpeed = (fanSpeed + 1) % 4; // Melakukan penambahan kecepatan kipas
    updateFanSpeed(fanSpeed); // Mengatur kecepatan kipas berdasarkan nilai fanSpeed
    fanButtonState = LOW;
  } else if (digitalRead(Fan_Button) == HIGH) {
    fanButtonState = HIGH;
  }
  
  if (Serial.available()) {
    command = Serial.readStringUntil('\n');
    command.trim();
    if (command.equals("ac_hidup")) {
      digitalWrite(AC_OnOff_button, HIGH);
      delay(200);
      digitalWrite(AC_OnOff_button,LOW);
    }
    else if (command.equals("ac_mati")) {
      digitalWrite(AC_OnOff_button, HIGH);
      delay(200);
      digitalWrite(AC_OnOff_button,LOW);
    }
    else if (command.equals("ac_naik")) {
      digitalWrite(AC_Up_button, HIGH);
      delay(200);
      digitalWrite(AC_Up_button,LOW);
    }
    else if (command.equals("ac_turun")) {
      digitalWrite(AC_Down_button, HIGH);
      delay(200);
      digitalWrite(AC_Down_button,LOW);
    }
    else if (command.equals("kunci_hidup")) {
      digitalWrite(Solenoid_DoorLock, LOW);
    }
    else if (command.equals("kunci_mati")) {
      digitalWrite(Solenoid_DoorLock, HIGH);
    }
    else if (command.equals("kran_hidup")) {
      digitalWrite(Solenoid_Valve, HIGH);
    }
    else if (command.equals("kran_mati")) {
      digitalWrite(Solenoid_Valve, LOW);
    }
    else if (command.equals("lampu1_hidup")) {
      digitalWrite(Lamp_Utama, HIGH);
    }
    else if (command.equals("lampu1_mati")) {
      digitalWrite(Lamp_Utama, LOW);
    }
    else if (command.equals("lampu2_hidup")) {
      digitalWrite(Lamp_Kamar, HIGH);
    }
    else if (command.equals("lampu2_mati")) {
      digitalWrite(Lamp_Kamar, LOW);
    }
    else if (command.equals("lampu3_hidup")) {
      digitalWrite(Lamp_Tamu, HIGH);
    }
    else if (command.equals("lampu3_mati")) {
      digitalWrite(Lamp_Tamu, LOW);
    }
    else if (command.equals("pompa_hidup")) {
      digitalWrite(WaterPump, HIGH);
      digitalWrite(Solenoid_Valve, HIGH);
    }
    else if (command.equals("pompa_mati")) {
      digitalWrite(WaterPump, LOW);
      digitalWrite(Solenoid_Valve, LOW);
    }
    else if (command.equals("terminal_hidup")) {
      digitalWrite(Terminal, HIGH);
    }
    else if (command.equals("terminal_mati")) {
      digitalWrite(Terminal, LOW);
    }
    
    else if (command.equals("kipas_hidup")) {
      digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);
      analogWrite(ENB, 80);
    }
    else if (command.equals("kipas_naik")) {
      digitalWrite(IN3, LOW); digitalWrite(IN4, LOW); delay(100);
      digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);
      analogWrite(ENB, 100);
    }
    else if (command.equals("kipas_turun")) {
      digitalWrite(IN3, LOW); digitalWrite(IN4, LOW); delay(100);
      digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);
      analogWrite(ENB, 60);
    }
    else if (command.equals("kipas_mati")) {
      digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
    }

    else if (command.equals("tirai_mati")) {
      digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
      analogWrite(ENA, 73); delay(152);
      digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
    }
    else if (command.equals("tirai_hidup")) {
      digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);
      analogWrite(ENA, 55); delay(117);
      digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);  
    }
    else if (command.equals("otolampu_hidup")) {
      digitalWrite(Oto_Lamp, HIGH);
    }
    else if (command.equals("otolampu_mati")) {
      digitalWrite(Oto_Lamp, LOW);
    }
    else if (command.equals("otopompa_hidup")) {
      digitalWrite(Oto_Pump, HIGH);
    }
    else if (command.equals("otopompa_mati")) {
      digitalWrite(Oto_Pump, LOW);
    }
    else if (command.equals("pergi")) {
      digitalWrite(Solenoid_Valve, LOW);
      digitalWrite(Lamp_Utama, LOW);
      digitalWrite(Lamp_Kamar, LOW);
      digitalWrite(Lamp_Tamu, LOW);
      digitalWrite(WaterPump, LOW);
      digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
      digitalWrite(Oto_Lamp, LOW);
      digitalWrite(Oto_Pump, LOW); 
      digitalWrite(Terminal, LOW); 
    }
    else if (command.equals("lampusemua_hidup")) {
      digitalWrite(Lamp_Utama, HIGH);
      digitalWrite(Lamp_Kamar, HIGH);
      digitalWrite(Lamp_Tamu, HIGH);
    }
    else if (command.equals("lampusemua_mati")) {
      digitalWrite(Lamp_Utama, LOW);
      digitalWrite(Lamp_Kamar, LOW);
      digitalWrite(Lamp_Tamu, LOW);
    }  
    Serial.print("Command: ");
    Serial.println(command);
  }
}
void checkPushButton(int buttonPin, int devicePin) {
  static int lastButtonState = HIGH;  // Asumsikan keadaan awal adalah HIGH (tidak ditekan)
  int buttonState = digitalRead(buttonPin);

  if (buttonState == LOW && lastButtonState == HIGH) {
    // Button ditekan
    digitalWrite(devicePin, !digitalRead(devicePin));  // Alihkan status perangkat
    delay(200);  // Debounce delay
  }

  lastButtonState = buttonState;  // Simpan keadaan saat ini untuk iterasi berikutnya
}
void updateFanSpeed(int speed) {
  switch (speed) {
    case 0:
      digitalWrite(IN3, LOW);
      digitalWrite(IN4, LOW);
      break;
    case 1:
      digitalWrite(IN3, LOW);
      digitalWrite(IN4, HIGH);
      analogWrite(ENB, 80);
      break;
    case 2:
      digitalWrite(IN3, LOW);
      digitalWrite(IN4, HIGH);
      analogWrite(ENB, 100);
      break;
    case 3:
      digitalWrite(IN3, LOW);
      digitalWrite(IN4, HIGH);
      analogWrite(ENB, 60);
      break;
    default:
      break;
  }
}
