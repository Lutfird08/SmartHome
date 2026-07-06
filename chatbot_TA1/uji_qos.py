import paho.mqtt.client as mqtt
import time
import sys

# ==========================================
# KONFIGURASI PENGUJIAN QoS
# ==========================================
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
TEST_TOPIC = "smart_home/qos_test"
QOS_LEVEL = 0  # Sesuai dengan QoS di sistem web kamu
TOTAL_MESSAGES = 100  # Jumlah paket data yang akan diuji
DELAY_ANTAR_PESAN = 0.5  # Jeda pengiriman 50ms (simulasi traffic padat)

# Variabel penyimpan data analitik
sent_data = {}
received_latencies = []
total_bytes_received = 0
waktu_mulai_terima = 0
waktu_akhir_terima = 0

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Terhubung ke Broker untuk Pengujian QoS!")
        client.subscribe(TEST_TOPIC, qos=QOS_LEVEL)
    else:
        print(f"❌ Gagal koneksi, kode: {rc}")
        sys.exit()

def on_message(client, userdata, msg):
    global total_bytes_received, waktu_mulai_terima, waktu_akhir_terima
    waktu_terima = time.time()
    
    # Hitung byte yang diterima untuk Throughput
    payload_size = sys.getsizeof(msg.payload)
    total_bytes_received += payload_size
    
    # Catat waktu terima pertama dan terakhir
    if waktu_mulai_terima == 0:
        waktu_mulai_terima = waktu_terima
    waktu_akhir_terima = waktu_terima

    # Ekstraksi payload untuk hitung Latency
    payload_str = msg.payload.decode("utf-8")
    try:
        msg_id, waktu_kirim_str = payload_str.split('|')
        waktu_kirim = float(waktu_kirim_str)
        
        # Hitung selisih waktu (Delay) dalam milidetik (ms)
        latency_ms = (waktu_terima - waktu_kirim) * 1000
        received_latencies.append(latency_ms)
        
        # Print proses agar terlihat di terminal
        print(f"📥 Diterima Paket {msg_id}/100 | Delay: {latency_ms:.2f} ms")
    except ValueError:
        pass

# Inisialisasi MQTT Client
client = mqtt.Client(client_id="tester_qos_skripsi")
client.on_connect = on_connect
client.on_message = on_message

print("Menghubungkan ke server...")
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

# Tunggu sebentar agar koneksi stabil
time.sleep(2)

print(f"\n🚀 MEMULAI PENGUJIAN QoS: Mengirim {TOTAL_MESSAGES} Pesan...\n")

# Mulai siklus pengiriman 100 pesan
for i in range(1, TOTAL_MESSAGES + 1):
    waktu_sekarang = time.time()
    # Payload format: ID_PESAN|WAKTU_KIRIM
    payload = f"{i}|{waktu_sekarang}"
    
    client.publish(TEST_TOPIC, payload, qos=QOS_LEVEL)
    time.sleep(DELAY_ANTAR_PESAN)

print("\n⏳ Pengiriman selesai. Menunggu sisa paket yang mungkin delay di jaringan (3 detik)...")
time.sleep(3)

client.loop_stop()

# ==========================================
# PERHITUNGAN DAN HASIL ANALISIS (BAB 4)
# ==========================================
print("\n" + "="*45)
print(" 📊 HASIL PENGUJIAN QoS JARINGAN SMART HOME")
print("="*45)

# 1. Packet Loss
paket_diterima = len(received_latencies)
packet_loss = ((TOTAL_MESSAGES - paket_diterima) / TOTAL_MESSAGES) * 100
print(f"📦 Total Paket Dikirim  : {TOTAL_MESSAGES}")
print(f"📥 Total Paket Diterima : {paket_diterima}")
print(f"📉 Packet Loss          : {packet_loss:.2f} %")

# 2. Delay / Latency
if paket_diterima > 0:
    avg_delay = sum(received_latencies) / paket_diterima
    min_delay = min(received_latencies)
    max_delay = max(received_latencies)
    print(f"\n⏱️  Delay Terendah       : {min_delay:.2f} ms")
    print(f"⏱️  Delay Tertinggi      : {max_delay:.2f} ms")
    print(f"⏱️  Rata-rata Delay      : {avg_delay:.2f} ms")
else:
    print("\n⏱️  Rata-rata Delay      : N/A (Tidak ada paket diterima)")

# 3. Throughput
durasi_total = waktu_akhir_terima - waktu_mulai_terima
if durasi_total > 0:
    throughput_bps = (total_bytes_received * 8) / durasi_total  # bits per second
    throughput_kbps = throughput_bps / 1024
    print(f"\n🚀 Total Durasi Terima  : {durasi_total:.2f} detik")
    print(f"🚀 Throughput           : {throughput_kbps:.2f} Kbps")
else:
    print("\n🚀 Throughput           : N/A")

print("="*45)
print("Gunakan data di atas untuk dilampirkan ke dalam Tabel Pengujian Bab 4.\n")