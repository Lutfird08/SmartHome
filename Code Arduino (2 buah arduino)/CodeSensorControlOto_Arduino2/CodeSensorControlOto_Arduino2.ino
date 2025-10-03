#include <DHT.h>
#define DHTPIN 2    // Pin data sensor DHT11 terhubung ke pin 2
#define DHTTYPE DHT11   // Tipe sensor DHT yang digunakan (DHT11 atau DHT22)
DHT dht(DHTPIN, DHTTYPE);

const int pinLDR = A0;
const int LDR_Lampu = 45;
const int soilMoisturePin = A1;
const int Soil_Pump = 51;

boolean suhuHasBeenRead = false;
void setup() {
  // put your setup code here, to run once:
Serial.begin(115200);
  pinMode(pinLDR, INPUT);
  pinMode(LDR_Lampu, OUTPUT);
  pinMode(soilMoisturePin, INPUT);
  pinMode(Soil_Pump, OUTPUT);

  dht.begin();
}

void loop() {
  // put your main code here, to run repeatedly:
float temperature = dht.readTemperature();
   int rounded_temperature = round(temperature);
   Serial.print("suhu:");
   Serial.println(rounded_temperature);
   delay(2000);
  
  int nilaiLDR = analogRead(pinLDR); // Membaca nilai sensor LDR
  int ambangNyala = 890; // Nilai ambang untuk menyalakan lampu
  int ambangMati = 889; // Nilai ambang untuk mematikan lampu
  int soilMoisture = analogRead(soilMoisturePin);
  int batasTanah = 700;
   
   
if (nilaiLDR > ambangNyala) {
    digitalWrite(LDR_Lampu, HIGH); // Menyalakan lampu
    delay(2000);} 
  else if (nilaiLDR < ambangMati) {
    digitalWrite(LDR_Lampu, LOW); // Mematikan lampu
    delay(2000);
  }
if (soilMoisture > batasTanah) {
    digitalWrite(Soil_Pump, HIGH);
    delay(2000);}
  else if (soilMoisture < batasTanah) {
    digitalWrite(Soil_Pump, LOW);
    delay(2000);
  }

}
