#include <WiFi.h>
#include <PubSubClient.h>

// ===== KONFIGURASI WIFI =====
const char* ssid = "LR";      // WiFi SSID
const char* password = "lutfird08";  // WiFi Password

// ===== KONFIGURASI MQTT =====
const char* mqtt_server = "broker.emqx.io";  // Broker EMQX
const int mqtt_port = 1883;                  // Port MQTT standar

// ===== TOPIK MQTT =====
const char* TOPIC_CONTROL = "smart_home/control";      // Menerima perintah dari web
const char* TOPIC_RESPONSE = "smart_home/response";    // Mengirim response ke web
const char* TOPIC_STATUS = "smart_home/status";        // Mengirim status ke web
const char* TOPIC_SENSOR = "smart_home/sensor";        // Mengirim data sensor

// ===== VARIABEL GLOBAL =====
WiFiClient espClient;
PubSubClient client(espClient);

// Buffer untuk data serial
String serialBuffer = "";
unsigned long lastReconnectAttempt = 0;
const unsigned long RECONNECT_INTERVAL = 5000;

// ===== KONEKSI WIFI =====
void setup_wifi() {
  delay(10);

  Serial.println();
  Serial.println("==================================");
  Serial.println("ESP32 MQTT Bridge");
  Serial.println("Serial2: Connected to Arduino Mega");
  Serial.println("==================================");

  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ WiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n❌ Failed to connect to WiFi");
  }
}

// ===== CALLBACK MQTT =====
void callback(char* topic, byte* payload, unsigned int length) {
  String message = "";
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

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

// ===== RECONNECT MQTT =====
void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");

    String clientId = "ESP32Client-";
    clientId += String(random(0xffff), HEX);

    if (client.connect(clientId.c_str())) {
      Serial.println("✅ MQTT connected!");

      // Subscribe ke topic control
      client.subscribe(TOPIC_CONTROL);
      Serial.print("Subscribed to: ");
      Serial.println(TOPIC_CONTROL);

      // Kirim status connected
      client.publish(TOPIC_RESPONSE, "ESP32: Connected to MQTT");

      // Kirim ping ke Arduino
      Serial2.println("PING");

    } else {
      Serial.print("❌ Failed, rc=");
      Serial.print(client.state());
      Serial.println(" - Retry in 5 seconds");
      delay(5000);
    }
  }
}

// ===== FILTER PESAN DARI ARDUINO =====
bool shouldForwardToMQTT(String message) {
  if (message.length() == 0) return false;

  // Skip system messages
  if (message.startsWith("ARDUINO_MEGA:") ||
      message.indexOf("SISTEM KONTROL") != -1 ||
      message.indexOf("PERINTAH SERIAL") != -1 ||
      message.startsWith("Catatan:") ||
      message.indexOf("======================") != -1 ||
      message.indexOf("=== STATUS") != -1 ||
      message.indexOf("PERANGKAT YANG") != -1) {
    return false;
  }

  // Skip ping responses
  if (message.startsWith("ARDUINO:ALIVE") ||
      message.startsWith("PING")) {
    return false;
  }

  // Skip empty lines or sensor separator
  String trimmedMsg = message;
  trimmedMsg.trim();
  if (message == "---" || trimmedMsg.length() == 0) {
    return false;
  }

  return true;
}

// ===== TENTUKAN TOPIK UNTUK PESAN =====
const char* getTopicForMessage(String message) {
  // Data sensor
  if (message.startsWith("LDR:") ||
      message.startsWith("Soil:") ||
      message.indexOf("DHT11") != -1 ||
      message.startsWith("SENSOR:")) {
    return TOPIC_SENSOR;
  }

  // Status perangkat (gunakan indexOf() bukan contains())
  if (message.indexOf(":ON") != -1 ||
      message.indexOf(":OFF") != -1 ||
      message.indexOf(":AKTIF") != -1 ||
      message.indexOf(":BUKA") != -1 ||
      message.indexOf(":TUTUP") != -1) {
    return TOPIC_STATUS;
  }

  // Error atau response
  if (message.startsWith("ERROR:") ||
      message.indexOf("Tombol ") != -1 ||
      message.startsWith("Kipas:") ||
      message.indexOf("Solenoid Door:") != -1 ||
      message.indexOf("Tirai:") != -1) {
    return TOPIC_RESPONSE;
  }

  // Default ke response
  return TOPIC_RESPONSE;
}

// ===== SETUP =====
void setup() {
  // Inisialisasi Serial untuk debugging
  Serial.begin(115200);
  delay(100);

  // Inisialisasi Serial2 untuk komunikasi dengan Arduino Mega
  // ESP32: RX2 = GPIO16, TX2 = GPIO17
  Serial2.begin(115200, SERIAL_8N1, 16, 17);
  delay(100);

  // Setup WiFi
  setup_wifi();

  // Setup MQTT
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  client.setBufferSize(1024);

  Serial.println("✅ ESP32 MQTT Bridge Ready!");
  Serial.println("📡 Waiting for MQTT connection...");
}

// ===== LOOP UTAMA =====
void loop() {
  // Maintain MQTT connection
  if (!client.connected()) {
    unsigned long now = millis();
    if (now - lastReconnectAttempt > RECONNECT_INTERVAL) {
      lastReconnectAttempt = now;
      reconnect();
    }
  } else {
    client.loop();
  }

  // ===== BACA DATA DARI ARDUINO (Serial2) =====
  while (Serial2.available() > 0) {
    char c = Serial2.read();

    if (c == '\n') {
      serialBuffer.trim();

      if (serialBuffer.length() > 0) {
        Serial.print("[FROM ARDUINO]: ");
        Serial.println(serialBuffer);

        // Forward ke MQTT jika perlu
        if (shouldForwardToMQTT(serialBuffer)) {
          const char* targetTopic = getTopicForMessage(serialBuffer);

          Serial.print("📤 Forwarding to MQTT [");
          Serial.print(targetTopic);
          Serial.print("]: ");
          Serial.println(serialBuffer);

          client.publish(targetTopic, serialBuffer.c_str());
        } else {
          Serial.println("⏭️  Filtered out (system message)");
        }
      }

      serialBuffer = "";
    }
    else if (c != '\r') {
      serialBuffer += c;
    }
  }

  // ===== PERIKSA STATUS WIFI =====
  static unsigned long lastWifiCheck = 0;
  if (millis() - lastWifiCheck > 30000) {
    lastWifiCheck = millis();

    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("⚠️ WiFi disconnected! Reconnecting...");
      WiFi.reconnect();
    }
  }

  // ===== KIRIM HEARTBEAT =====
  static unsigned long lastHeartbeat = 0;
  if (millis() - lastHeartbeat > 30000) { // Setiap 30 detik
    lastHeartbeat = millis();

    if (client.connected()) {
      String heartbeat = "ESP32: Online - Uptime: " + String(millis() / 1000) + "s";
      client.publish(TOPIC_RESPONSE, heartbeat.c_str());
      Serial.println("💓 Heartbeat sent");

      // Kirim ping ke Arduino
      Serial2.println("PING");
    }
  }

  // Small delay
  delay(10);
}
