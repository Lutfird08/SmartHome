// ==========================================
//  HOME.JS - SMART HOME FINAL VERSION
// ==========================================

// --- 1. KONFIGURASI MQTT ---
const MQTT_BROKER_URL = 'wss://broker.emqx.io:8084/mqtt';
const MQTT_TOPIC_PREFIX = 'lutfi_140910/smart_home/';

let mqttClient = null;
let isConnected = false;

// --- 2. MAPPING PERANGKAT (Arduino Name -> HTML ID) ---
// Kiri: Nama yang dikirim Arduino (Huruf Kecil)
// Kanan: ID elemen HTML yang akan diubah warnanya
const deviceMap = {
    "lampu utama": "lamp",
    "lampu kamar": "lamp", // Opsional: jika ingin icon sama
    "solenoid door": "door",
    "ac": "status-ac"      // ID ini ada di halaman AC (ac.html) atau home.html
};

// --- 3. KONEKSI MQTT ---
function connectToMQTT() {
    console.log('Menghubungkan ke MQTT...');
    
    // Buat ID Client unik agar tidak bentrok
    const options = {
        clientId: 'WebClient_' + Math.random().toString(16).substr(2, 8),
        clean: true,
        reconnectPeriod: 5000,
    };

    mqttClient = mqtt.connect(MQTT_BROKER_URL, options);

    mqttClient.on('connect', function () {
        console.log('✅ Terhubung ke MQTT!');
        isConnected = true;
        updateConnectionStatus(true);
        
        // Subscribe ke SEMUA topik (input, reply, status, sensor)
        mqttClient.subscribe(MQTT_TOPIC_PREFIX + '#');
        
        // PENTING: Minta status awal ke Arduino agar tidak "Unknown"
        // Diberi jeda 1.5 detik agar koneksi stabil dulu
        setTimeout(() => {
            console.log("Meminta status awal...");
            sendToPython("STATUS");
        }, 1500); 
    });

    mqttClient.on('message', function (topic, message) {
        handleIncomingMessage(topic, message.toString());
    });

    mqttClient.on('close', () => updateConnectionStatus(false));
    mqttClient.on('error', (err) => console.error('MQTT Error:', err));
}

// --- 4. HANDLER PESAN MASUK ---
function handleIncomingMessage(topic, message) {
    // A. DATA SENSOR (Tampilkan di Chat)
    // Format Arduino: "SENSOR: LDR:100, Soil:200, Temp:28.00"
    if (message.startsWith("SENSOR:")) {
        const cleanMsg = message.replace("SENSOR:", "").trim();
        addChatMessage('Sensor', cleanMsg);
        return;
    }

    // B. SUARA BOT (Dari Python)
    if (topic.includes('voice_reply')) {
        addChatMessage('Bot', message);
        speak(message);
        return;
    }

    // C. STATUS REALTIME (Update Icon & Teks)
    // Format Arduino: "Nama Alat: Status"
    if (message.includes(':')) {
        const parts = message.split(':');
        if (parts.length >= 2) {
            const devName = parts[0].trim().toLowerCase();
            const devStatus = parts[1].trim();
            
            updateUIFromResponse(devName, devStatus);
        }
    }
}

// --- 5. UPDATE TAMPILAN (UI) ---
function updateUIFromResponse(name, status) {
    // Loop mapping untuk mencocokkan nama alat
    for (const [key, elementId] of Object.entries(deviceMap)) {
        if (name.includes(key)) {
            const el = document.getElementById(elementId);
            
            // Hanya update jika elemen ada di halaman ini
            if (el) {
                // Cek status ON/OFF
                const isNyala = status.toUpperCase() === 'ON' || 
                                status.toUpperCase() === 'TERBUKA' ||
                                status.toUpperCase().includes('NYALA');
                
                // Ubah Teks sesuai jenis alat
                if (elementId === 'door') {
                    el.innerText = isNyala ? "Terbuka" : "Terkunci";
                } else {
                    el.innerText = isNyala ? "Nyala" : "Mati";
                }

                // Ubah Warna (Hijau = Aktif, Merah = Mati)
                el.style.color = isNyala ? "#4CAF50" : "#f44336";
                el.style.fontWeight = "bold";
            }
        }
    }
}

// --- 6. KIRIM PERINTAH ---
function sendToPython(text) {
    if (isConnected) {
        // Kirim ke topik voice_input agar Python yang memproses
        mqttClient.publish(MQTT_TOPIC_PREFIX + 'voice_input', text.toLowerCase());
        console.log("Dikirim:", text);
    } else {
        alert("Koneksi MQTT Putus! Cek internet.");
    }
}

function sendMessage() {
    const input = document.getElementById('userInput');
    const msg = input.value.trim();
    if (msg === '') return;

    addChatMessage('Anda', msg); // Tampilkan ketikan user
    sendToPython(msg);           // Kirim ke Python
    input.value = '';            // Kosongkan input
}

// --- 7. FITUR CHAT & SUARA ---
function addChatMessage(sender, message) {
    const chatBox = document.getElementById('chatMessages');
    if (!chatBox) return;
    
    const div = document.createElement('div');
    
    // Style dasar pesan
    div.style.marginBottom = '10px';
    div.style.padding = '10px';
    div.style.borderRadius = '10px';
    div.style.maxWidth = '85%';
    div.style.fontSize = '14px';
    div.style.lineHeight = '1.4';
    
    // Style berbeda tiap pengirim
    if (sender === 'Anda') {
        div.style.marginLeft = 'auto';
        div.style.backgroundColor = '#e3f2fd'; // Biru muda
        div.style.textAlign = 'right';
        div.innerHTML = `<strong>${sender}</strong><br>${message}`;
    } else if (sender === 'Sensor') {
        div.style.marginRight = 'auto';
        div.style.backgroundColor = '#fff3e0'; // Kuning muda (Sensor)
        div.style.border = '1px solid #ffe0b2';
        div.innerHTML = `<strong>📡 Data Sensor</strong><br>${message}`;
    } else if (sender === 'System') {
        div.style.margin = '15px auto';
        div.style.backgroundColor = '#e8f5e9'; // Hijau muda (Info)
        div.style.textAlign = 'center';
        div.style.width = '90%';
        div.innerHTML = `${message}`;
    } else { // Bot
        div.style.marginRight = 'auto';
        div.style.backgroundColor = '#f5f5f5'; // Abu muda
        div.innerHTML = `<strong>${sender}</strong><br>${message}`;
    }
    
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight; // Auto scroll ke bawah
}

// Text to Speech (Web Bicara)
function speak(text) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel(); // Stop suara sebelumnya
        const u = new SpeechSynthesisUtterance(text);
        u.lang = 'id-ID'; // Bahasa Indonesia
        window.speechSynthesis.speak(u);
    }
}

// Speech to Text (Web Mendengar)
function startVoiceRecognition() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert("Browser ini tidak mendukung fitur suara. Gunakan Chrome."); return;
    }
    const Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new Rec();
    recognition.lang = 'id-ID';
    recognition.start();

    addChatMessage('System', '🎤 Mendengarkan suara Anda...');

    recognition.onresult = (e) => {
        const txt = e.results[0][0].transcript;
        addChatMessage('Anda', txt);
        sendToPython(txt);
    };
}

// --- 8. STATUS KONEKSI & WAKTU ---
function updateConnectionStatus(connected) {
    const els = document.querySelectorAll('.status-text');
    els.forEach(el => {
        // Hanya ubah jika status masih Unknown/Loading
        if (el.innerText === 'Unknown' || el.innerText === 'Loading...') {
            el.innerText = connected ? "Mati" : "Offline"; // Default aman
            el.style.color = connected ? "#f44336" : "#9e9e9e";
        }
    });
}

function updateDateTime() {
    const now = new Date();
    const elTime = document.querySelector('.time');
    const elDate = document.querySelector('.date');
    if(elTime) elTime.innerText = now.toLocaleTimeString('id-ID', {hour:'2-digit', minute:'2-digit'});
    if(elDate) elDate.innerText = now.toLocaleDateString('id-ID', {weekday:'long', day:'numeric', month:'long', year:'numeric'});
}

// --- 9. INITIALIZATION (SAAT HALAMAN DIMUAT) ---
window.onload = function() {
    // 1. Jalankan Jam
    updateDateTime();
    setInterval(updateDateTime, 60000);
    
    // 2. Koneksi ke MQTT
    connectToMQTT();
    
    // 3. Tampilkan Pesan Selamat Datang (Delay 1 detik)
    setTimeout(() => {
        const welcomeText = `
            <strong>👋 Selamat Datang di Smart Home!</strong><br><br>
            Silakan coba perintah suara atau ketik:<br>
            💡 "Nyalakan lampu utama"<br>
            🚪 "Buka pintu"<br>
            ❄️ "Nyalakan AC"<br>
            🌡️ "Berapa suhu sekarang?"
        `;
        addChatMessage('System', welcomeText);
    }, 1000);

    // 4. Listener tombol Enter di keyboard
    const input = document.getElementById('userInput');
    if (input) {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }
};

// Export fungsi ke HTML agar bisa diklik
window.sendMessage = sendMessage;
window.startVoiceRecognition = startVoiceRecognition;
window.sendToPython = sendToPython;
window.toggleMenu = () => document.getElementById('hamburgerMenu').classList.toggle('active');
