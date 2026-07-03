#include <WiFi.h>
#include <PubSubClient.h>

// ===== KONFIGURASI WIFI =====
const char* ssid     = "LR";
const char* password = "lutfird08";

// ===== KONFIGURASI MQTT =====
const char* mqtt_server = "broker.emqx.io";
const int   mqtt_port   = 1883;

// ===== TOPIK MQTT =====
const char* TOPIC_CONTROL  = "smart_home/control";
const char* TOPIC_RESPONSE = "smart_home/response";
const char* TOPIC_STATUS   = "smart_home/status";
const char* TOPIC_SENSOR   = "smart_home/sensor";

// ===== VARIABEL GLOBAL =====
WiFiClient   espClient;
PubSubClient client(espClient);

String        serialBuffer        = "";
unsigned long lastReconnectAttempt = 0;
unsigned long lastWifiCheck        = 0;
unsigned long lastHeartbeat        = 0;

// ===== KONEKSI WIFI =====
void setup_wifi() {
  delay(10);
  Serial.println("==================================");
  Serial.println("ESP32 MQTT Bridge");
  Serial.println("Serial2: Connected to Arduino Mega");
  Serial.println("==================================");
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 40) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n❌ Failed to connect to WiFi — akan retry otomatis");
  }
}

// ===== CALLBACK MQTT — dipanggil saat pesan masuk =====
void callback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
  message.trim();

  Serial.print("📩 Received from MQTT [");
  Serial.print(topic);
  Serial.print("]: ");
  Serial.println(message);

  // Kirim ke Arduino Mega via Serial2
  Serial2.println(message);
  Serial.print("➡️  Sent to Arduino: ");
  Serial.println(message);

  // Kirim konfirmasi ke web
  String response = "Command received: " + message;
  client.publish(TOPIC_RESPONSE, response.c_str());
}

// ===== RECONNECT MQTT (NON-BLOCKING) =====
// FIX UTAMA: tidak pakai while() — hanya 1 attempt per panggilan
// sehingga client.loop() tetap berjalan dan pesan tidak terlewat
bool reconnectMQTT() {
  if (client.connected()) return true;

  Serial.print("Attempting MQTT connection... ");

  String clientId = "ESP32Client-";
  clientId += String(random(0xffff), HEX);

  if (client.connect(clientId.c_str())) {
    Serial.println("✅ MQTT connected!");

    // Subscribe ulang setiap kali konek (wajib!)
    client.subscribe(TOPIC_CONTROL);
    Serial.print("Subscribed to: ");
    Serial.println(TOPIC_CONTROL);

    client.publish(TOPIC_RESPONSE, "ESP32: Connected to MQTT");
    Serial2.println("PING");
    return true;

  } else {
    Serial.print("❌ Failed, rc=");
    Serial.print(client.state());
    Serial.println(" — retry 5 detik lagi");
    return false;
  }
}

// ===== FILTER PESAN DARI ARDUINO =====
bool shouldForwardToMQTT(String message) {
  if (message.length() == 0) return false;

  if (message.startsWith("ARDUINO_MEGA:") ||
      message.indexOf("SISTEM KONTROL")  != -1 ||
      message.indexOf("PERINTAH SERIAL") != -1 ||
      message.startsWith("Catatan:")     ||
      message.indexOf("======================") != -1 ||
      message.indexOf("=== STATUS")      != -1 ||
      message.indexOf("PERANGKAT YANG")  != -1) {
    return false;
  }

  if (message.startsWith("ARDUINO:ALIVE") ||
      message.startsWith("PING")) {
    return false;
  }

  String trimmedMsg = message;
  trimmedMsg.trim();
  if (message == "---" || trimmedMsg.length() == 0) return false;

  return true;
}

// ===== TENTUKAN TOPIK UNTUK PESAN DARI ARDUINO =====
const char* getTopicForMessage(String message) {
  // Data sensor — format Arduino: "ldr:nilai", "temperature:nilai", dll
  if (message.startsWith("ldr:")         ||
      message.startsWith("soil:")        ||
      message.startsWith("humidity:")    ||
      message.startsWith("temperature:") ||
      message.startsWith("LDR:")         ||
      message.startsWith("Soil:")        ||
      message.indexOf("DHT11")   != -1   ||
      message.startsWith("SENSOR:")) {
    return TOPIC_SENSOR;
  }

  // Status perangkat
  if (message.indexOf(":ON")    != -1 ||
      message.indexOf(":OFF")   != -1 ||
      message.indexOf(":AKTIF") != -1 ||
      message.indexOf(":BUKA")  != -1 ||
      message.indexOf(":TUTUP") != -1 ||
      message.indexOf(":PULSE") != -1) {
    return TOPIC_STATUS;
  }

  return TOPIC_RESPONSE;
}

// ===== SETUP =====
void setup() {
  Serial.begin(115200);
  delay(100);

  // Serial2 untuk komunikasi dengan Arduino Mega
  // RX2 = GPIO16, TX2 = GPIO17
  Serial2.begin(115200, SERIAL_8N1, 16, 17);
  delay(100);

  setup_wifi();

  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  client.setBufferSize(1024);

  Serial.println("✅ ESP32 MQTT Bridge Ready!");
}

// ===== LOOP UTAMA =====
void loop() {

  // ── Maintain WiFi ──
  if (millis() - lastWifiCheck > 30000) {
    lastWifiCheck = millis();
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("⚠️ WiFi disconnected! Reconnecting...");
      WiFi.reconnect();
    }
  }

  // ── Maintain MQTT (NON-BLOCKING) ──
  if (!client.connected()) {
    unsigned long now = millis();
    if (now - lastReconnectAttempt > 5000) {
      lastReconnectAttempt = now;
      reconnectMQTT();
    }
    // Tidak return di sini — biarkan loop terus jalan
  }

  // ── Proses pesan MQTT yang masuk ──
  // client.loop() HARUS selalu dipanggil, connected maupun tidak
  client.loop();

  // ── Baca data dari Arduino via Serial2 ──
  while (Serial2.available() > 0) {
    char c = Serial2.read();

    if (c == '\n') {
      serialBuffer.trim();

      if (serialBuffer.length() > 0) {
        Serial.print("[FROM ARDUINO]: ");
        Serial.println(serialBuffer);

        if (shouldForwardToMQTT(serialBuffer)) {
          const char* targetTopic = getTopicForMessage(serialBuffer);
          Serial.print("📤 Forwarding to MQTT [");
          Serial.print(targetTopic);
          Serial.print("]: ");
          Serial.println(serialBuffer);
          client.publish(targetTopic, serialBuffer.c_str());
        } else {
          Serial.println("⏭️  Filtered out");
        }
      }

      serialBuffer = "";
    }
    else if (c != '\r') {
      serialBuffer += c;
    }
  }

  // ── Heartbeat setiap 30 detik ──
  if (millis() - lastHeartbeat > 30000) {
    lastHeartbeat = millis();
    if (client.connected()) {
      String hb = "ESP32: Online - Uptime: " + String(millis() / 1000) + "s";
      client.publish(TOPIC_RESPONSE, hb.c_str());
      Serial.println("💓 Heartbeat sent");
      Serial2.println("PING");
    }
  }

  delay(10);
}
