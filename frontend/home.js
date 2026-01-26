// ==========================================
//  HOME.JS - SMART HOME FINAL (FIXED VOICE)
// ==========================================

// --- 1. KONFIGURASI MQTT ---
const MQTT_BROKER_URL = 'wss://broker.emqx.io:8084/mqtt';
const MQTT_TOPIC_PREFIX = 'lutfi_140910/smart_home/';

let mqttClient = null;
let isConnected = false;

// Variabel untuk menyimpan suara Indonesia
let indoVoice = null;

// --- 2. MAPPING PERANGKAT (Arduino Name -> HTML ID) ---
const deviceMap = {
    "lampu utama": "lamp",
    "lampu kamar": "lamp", 
    "solenoid door": "door",
    "ac": "status-ac"      
};

// --- 3. KONEKSI MQTT ---
function connectToMQTT() {
    console.log('Menghubungkan ke MQTT...');
    
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
        
        // Subscribe ke SEMUA topik
        mqttClient.subscribe(MQTT_TOPIC_PREFIX + '#');
        
        // Minta status awal ke Arduino (Jeda 1.5 detik agar stabil)
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
    // A. DATA SENSOR
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

    // C. STATUS REALTIME
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
    for (const [key, elementId] of Object.entries(deviceMap)) {
        if (name.includes(key)) {
            const el = document.getElementById(elementId);
            if (el) {
                const isNyala = status.toUpperCase().includes('ON') || 
                                status.toUpperCase().includes('TERBUKA') ||
                                status.toUpperCase().includes('NYALA');
                
                if (elementId === 'door') {
                    el.innerText = isNyala ? "Terbuka" : "Terkunci";
                } else {
                    el.innerText = isNyala ? "Nyala" : "Mati";
                }

                el.style.color = isNyala ? "#4CAF50" : "#f44336";
                el.style.fontWeight = "bold";
            }
        }
    }
}

// --- 6. KIRIM PERINTAH ---
function sendToPython(text) {
    if (isConnected) {
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

    addChatMessage('Anda', msg);
    sendToPython(msg);
    input.value = '';
}

// --- 7. FITUR CHAT & SUARA (YANG DIPERBAIKI) ---

// Fungsi Load Suara Indonesia
function loadVoices() {
    const voices = window.speechSynthesis.getVoices();
    // Cari suara Google Bahasa Indonesia atau ID-ID
    indoVoice = voices.find(v => v.name === 'Google Bahasa Indonesia') || 
                voices.find(v => v.lang === 'id-ID') || 
                voices.find(v => v.lang === 'id_ID');
    
    if (indoVoice) console.log("✅ Suara Indonesia dimuat:", indoVoice.name);
}

// Event listener saat suara browser siap
if ('speechSynthesis' in window) {
    window.speechSynthesis.onvoiceschanged = loadVoices;
}

// Fungsi Bicara
function speak(text) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        
        const u = new SpeechSynthesisUtterance(text);
        u.lang = 'id-ID';
        u.rate = 0.95; // Kecepatan sedikit lebih lambat agar jelas
        u.pitch = 1.0;
        
        // Paksa pakai suara Indonesia jika ketemu
        if (!indoVoice) loadVoices();
        if (indoVoice) u.voice = indoVoice;

        window.speechSynthesis.speak(u);
    }
}

// Fungsi Mendengar
function startVoiceRecognition() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert("Browser tidak support suara. Gunakan Chrome."); return;
    }
    const Rec = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new Rec();
    recognition.lang = 'id-ID';
    recognition.start();

    addChatMessage('System', '🎤 Mendengarkan...');

    recognition.onresult = (e) => {
        const txt = e.results[0][0].transcript;
        addChatMessage('Anda', txt);
        sendToPython(txt);
    };
}

function addChatMessage(sender, message) {
    const chatBox = document.getElementById('chatMessages');
    if (!chatBox) return;
    
    const div = document.createElement('div');
    
    // Styling
    div.style.marginBottom = '10px';
    div.style.padding = '10px';
    div.style.borderRadius = '10px';
    div.style.maxWidth = '85%';
    div.style.fontSize = '14px';
    
    if (sender === 'Anda') {
        div.style.marginLeft = 'auto';
        div.style.backgroundColor = '#e3f2fd';
        div.style.textAlign = 'right';
        div.innerHTML = `<strong>${sender}</strong><br>${message}`;
    } else if (sender === 'Sensor') {
        div.style.marginRight = 'auto';
        div.style.backgroundColor = '#fff3e0';
        div.style.border = '1px solid #ffe0b2';
        div.innerHTML = `<strong>📡 Data Sensor</strong><br>${message}`;
    } else if (sender === 'System') {
        div.style.margin = '15px auto';
        div.style.backgroundColor = '#e8f5e9';
        div.style.textAlign = 'center';
        div.style.width = '90%';
        div.innerHTML = `${message}`;
    } else { // Bot
        div.style.marginRight = 'auto';
        div.style.backgroundColor = '#f5f5f5';
        div.innerHTML = `<strong>${sender}</strong><br>${message}`;
    }
    
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

// --- 8. STATUS & WAKTU ---
function updateConnectionStatus(connected) {
    const els = document.querySelectorAll('.status-text');
    els.forEach(el => {
        if (el.innerText === 'Unknown' || el.innerText === 'Loading...') {
            el.innerText = connected ? "Mati" : "Offline";
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

// --- 9. INITIALIZATION ---
window.onload = function() {
    updateDateTime();
    setInterval(updateDateTime, 60000);
    connectToMQTT();
    
    // Load suara saat awal buka
    if ('speechSynthesis' in window) loadVoices();
    
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

    const input = document.getElementById('userInput');
    if (input) {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    }
};

window.sendMessage = sendMessage;
window.startVoiceRecognition = startVoiceRecognition;
window.sendToPython = sendToPython;
window.toggleMenu = () => document.getElementById('hamburgerMenu').classList.toggle('active');
