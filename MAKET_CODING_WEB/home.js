// ==========================================
//  HOME.JS — FIXED MQTT TOPIC & VOICE REPLY
//  + TEXT TO SPEECH (TTS) untuk balasan Asisten
// ==========================================

const MQTT_BROKER_URL   = 'wss://broker.emqx.io:8084/mqtt';
const MQTT_TOPIC_PREFIX = 'smart_home/';

const TOPIC_CONTROL     = MQTT_TOPIC_PREFIX + 'control';
const TOPIC_STATUS      = MQTT_TOPIC_PREFIX + 'status';
const TOPIC_SENSOR      = MQTT_TOPIC_PREFIX + 'sensor';
const TOPIC_VOICE_INPUT = MQTT_TOPIC_PREFIX + 'voice_input';
const TOPIC_VOICE_REPLY = MQTT_TOPIC_PREFIX + 'voice_reply';

let mqttClient   = null;
let isConnected  = false;

// =====================================================
// TEXT TO SPEECH (TTS) — Web Speech API
// Fix: Chrome Android butuh interaksi user dulu
// =====================================================
let ttsEnabled      = true;   // default: suara ON
let ttsVoice        = null;   // voice yang dipilih
let ttsUnlocked     = false;  // apakah sudah di-unlock oleh user
let ttsPendingQueue = [];      // antrian teks yang menunggu unlock

// Inisialisasi TTS — cari suara bahasa Indonesia
function initTTS() {
    if (!('speechSynthesis' in window)) {
        console.warn('Browser tidak mendukung TTS');
        ttsEnabled = false;
        return;
    }

    function loadVoices() {
        const voices = window.speechSynthesis.getVoices();
        ttsVoice = voices.find(v => v.lang === 'id-ID') ||
                   voices.find(v => v.lang.startsWith('id')) ||
                   voices[0] || null;
        if (ttsVoice) console.log('TTS Voice:', ttsVoice.name, ttsVoice.lang);
    }

    loadVoices();
    window.speechSynthesis.onvoiceschanged = loadVoices;

    // ── KUNCI UTAMA: unlock TTS saat user pertama kali sentuh layar ──
    // Chrome Android memblokir audio sampai ada interaksi user
    function unlockTTS() {
        if (ttsUnlocked) return;

        // Putar utterance kosong (silent) untuk "membuka kunci" audio context
        const silent = new SpeechSynthesisUtterance('');
        silent.volume = 0;
        silent.onend = () => {
            ttsUnlocked = true;
            console.log('✅ TTS unlocked!');

            // Putar semua teks yang tertunda saat masih terkunci
            if (ttsPendingQueue.length > 0) {
                const text = ttsPendingQueue.shift();
                speakNow(text);
                ttsPendingQueue = [];
            }
        };
        window.speechSynthesis.speak(silent);

        // Hapus listener setelah unlock berhasil
        document.removeEventListener('touchstart', unlockTTS);
        document.removeEventListener('click',      unlockTTS);
        document.removeEventListener('keydown',    unlockTTS);
    }

    // Dengarkan interaksi pertama user (tap, klik, atau ketik)
    document.addEventListener('touchstart', unlockTTS, { once: true });
    document.addEventListener('click',      unlockTTS, { once: true });
    document.addEventListener('keydown',    unlockTTS, { once: true });
}

// Fungsi internal untuk benar-benar bicara
function speakNow(text) {
    if (!('speechSynthesis' in window)) return;

    window.speechSynthesis.cancel();

    const utterance    = new SpeechSynthesisUtterance(text);
    utterance.lang     = 'id-ID';
    utterance.rate     = 1.0;
    utterance.pitch    = 1.0;
    utterance.volume   = 1.0;

    if (ttsVoice) utterance.voice = ttsVoice;

    // Workaround bug Chrome: TTS berhenti sendiri setelah 15 detik
    utterance.onstart = () => {
        const resumeTimer = setInterval(() => {
            if (window.speechSynthesis.speaking) {
                window.speechSynthesis.pause();
                window.speechSynthesis.resume();
            } else {
                clearInterval(resumeTimer);
            }
        }, 10000);
        utterance.onend = () => clearInterval(resumeTimer);
    };

    window.speechSynthesis.speak(utterance);
}

// Fungsi utama bicara — dipanggil dari luar
function speak(text) {
    if (!ttsEnabled) return;
    if (!('speechSynthesis' in window)) return;

    if (ttsUnlocked) {
        // Sudah unlock — langsung bicara
        speakNow(text);
    } else {
        // Belum unlock — simpan ke antrian, tunggu user tap layar
        ttsPendingQueue = [text]; // simpan hanya yang terbaru
        console.log('⏳ TTS pending (menunggu interaksi user):', text);
    }
}

// Toggle ON/OFF suara dari tombol di UI
function toggleTTS() {
    ttsEnabled = !ttsEnabled;
    const btn  = document.getElementById('ttsToggleBtn');
    if (btn) {
        btn.textContent = ttsEnabled ? '🔊' : '🔇';
        btn.title       = ttsEnabled ? 'Suara ON (klik untuk mute)' : 'Suara OFF (klik untuk unmute)';
        btn.style.backgroundColor = ttsEnabled ? '#4CAF50' : '#ccc';
    }
    addChatMessage('System', ttsEnabled ? '🔊 Suara asisten dinyalakan' : '🔇 Suara asisten dimatikan');
}

// =====================================================
// MAPPING PERINTAH — sesuai Arduino Mega (.ino)
// =====================================================
const deviceCommands = {
    0:  { on: 'ON 0',       off: 'OFF 0'    },
    1:  { on: 'ON 1',       off: 'OFF 1'    },
    2:  { on: 'ON 2',       off: 'OFF 2'    },
    3:  { on: 'ON 3',       off: 'OFF 3'    },
    6:  { on: 'KIPASON 50', off: 'KIPASOFF' },
    7:  { on: 'ON 7',       off: 'OFF 7'    },
    8:  { on: 'ON 8',       off: 'OFF 8'    },
    9:  { on: 'ON 9',       off: 'OFF 9'    },
    10: { on: 'ON 10',      off: 'OFF 10'   },
    11: { on: 'ON 11',      off: 'OFF 11'   },
    'ac_power': 'AC_POWER',
    'ac_up':    'AC_UP',
    'ac_down':  'AC_DOWN',
    'tirai_buka':  'TIRAIBUKA 45',
    'tirai_tutup': 'TIRAITUTUP 45',
    'tirai_stop':  'TIRAIOFF'
};

const deviceNames = {
    0: 'lampu_utama',   1: 'lampu_kamar',  2: 'lampu_tamu',
    3: 'colokan_terminal', 6: 'kipas',     7: 'pompa_penyiram',
    8: 'solenoid_valve', 9: 'solenoid_door',
    10: 'otomatis_pompa', 11: 'otomatis_lampu'
};

let deviceStatus = { lamp: 'Mati', ac: 'Mati', door: 'Terkunci' };

let allDeviceStatus = {
    0: false, 1: false, 2: false, 3: false,
    6: false, 7: false, 8: false, 9: false,
    ac: false
};

// =====================================================
// MQTT — KONEKSI
// =====================================================
function connectToMQTT() {
    const options = {
        clientId: 'smart_home_web_' + Math.random().toString(16).substr(2, 8),
        clean: true,
        reconnectPeriod: 1000,
        connectTimeout: 30000
    };

    mqttClient = mqtt.connect(MQTT_BROKER_URL, options);

    mqttClient.on('connect', () => {
        isConnected = true;
        subscribeToTopics();
        updateConnectionStatus(true);
        setTimeout(() => sendSerialCommand('STATUS'), 1000);
        addChatMessage('System', '✅ Terhubung ke Smart Home System');
    });

    mqttClient.on('message', (topic, message) => {
        handleIncomingMessage(topic, message.toString());
    });

    mqttClient.on('error', () => updateConnectionStatus(false));
    mqttClient.on('close', () => { isConnected = false; updateConnectionStatus(false); });
}

function subscribeToTopics() {
    [TOPIC_STATUS, TOPIC_SENSOR, TOPIC_VOICE_REPLY].forEach(t => {
        mqttClient.subscribe(t, { qos: 0 });
    });
}

// =====================================================
// HANDLE PESAN MASUK
// =====================================================
function handleIncomingMessage(topic, message) {
    if (message.includes("SISTEM KONTROL RUMAH") ||
        message.includes("PERINTAH SERIAL:")     ||
        message.includes("Catatan:")             ||
        message.startsWith("ARDUINO_MEGA:")      ||
        message.startsWith("ESP32:")             ||
        message.startsWith("Command received:")) return;

    // ── Balasan dari Voice Assistant (Raspberry Pi) ──
    if (topic === TOPIC_VOICE_REPLY) {
        addChatMessage('Asisten', message);
        speak(message);   // ← SUARA KELUAR DI SINI
        return;
    }

    if (topic === TOPIC_STATUS) { parseArduinoResponse(message); return; }
    if (topic === TOPIC_SENSOR) { processSensorData(message);    return; }
}

function parseArduinoResponse(message) {
    if (!message.includes(':')) return;

    const parts      = message.split(':');
    if (parts.length < 2) return;

    const deviceName = parts[0].trim().toLowerCase();
    const status     = parts[1].trim().toUpperCase();
    const isOn       = status.includes('ON')      || status.includes('AKTIF') ||
                       status.includes('NYALA')   || status.includes('BUKA')  ||
                       status.includes('TERBUKA') || status.includes('PULSE');

    addChatMessage('Arduino', `${parts[0].trim()}: ${parts[1].trim()}`);

    switch (deviceName) {
        case 'lampu_utama':
            allDeviceStatus[0] = isOn;
            updateDeviceStatus('lamp', isOn ? 'Nyala' : 'Mati');
            break;
        case 'lampu_kamar':      allDeviceStatus[1] = isOn; break;
        case 'lampu_tamu':       allDeviceStatus[2] = isOn; break;
        case 'colokan_terminal': allDeviceStatus[3] = isOn; break;
        case 'kipas':            allDeviceStatus[6] = isOn; break;
        case 'pompa_penyiram':   allDeviceStatus[7] = isOn; break;
        case 'solenoid_valve':   allDeviceStatus[8] = isOn; break;
        case 'solenoid_door':
            allDeviceStatus[9] = isOn;
            updateDeviceStatus('door', isOn ? 'Terbuka' : 'Terkunci');
            break;
        case 'ac_power':
            allDeviceStatus.ac = !allDeviceStatus.ac;
            updateDeviceStatus('ac', allDeviceStatus.ac ? 'Nyala' : 'Mati');
            break;
        case 'tirai':
            addChatMessage('System', `Tirai: ${parts[1].trim()}`);
            break;
    }
}

function processSensorData(message) {
    if (message.includes(':')) {
        addChatMessage('Sensor', message);
    }
}

// =====================================================
// KIRIM PERINTAH
// =====================================================
function sendSerialCommand(command) {
    if (!isConnected || !mqttClient) {
        addChatMessage('System', '❌ Tidak terhubung ke server MQTT');
        return false;
    }
    mqttClient.publish(TOPIC_CONTROL, command, { qos: 0 });
    return true;
}

function sendDeviceCommand(deviceIndex, action) {
    const cmd = deviceCommands[deviceIndex];
    if (!cmd) { addChatMessage('System', `Perangkat index ${deviceIndex} tidak dikenali`); return false; }
    const command = cmd[action];
    if (!command) { addChatMessage('System', `Perintah '${action}' tidak tersedia`); return false; }
    return sendSerialCommand(command);
}

// =====================================================
// CHAT — PROSES PERINTAH TEKS
// =====================================================
function sendMessage() {
    const input   = document.getElementById('userInput');
    const message = input.value.trim();
    if (!message) return;

    addChatMessage('Anda', message);

    const isDirectCommand = processDirectCommand(message);

    if (!isDirectCommand) {
        if (isConnected) {
            mqttClient.publish(TOPIC_VOICE_INPUT, message.toLowerCase(), { qos: 0 });
            addChatMessage('System', '⏳ Mengirim ke Asisten AI...');
        } else {
            addChatMessage('System', '❌ Tidak terhubung ke MQTT');
        }
    }

    input.value = '';
}

function processDirectCommand(message) {
    const msg = message.toLowerCase().trim();

    if (msg === 'status') {
        sendSerialCommand('STATUS');
        addChatMessage('System', '📋 Meminta status sistem...');
        return true;
    }

    if (msg.includes('nyala semua') || msg.includes('nyalakan semua')) {
        [0, 1, 2, 3, 6, 7, 8].forEach((id, i) => {
            setTimeout(() => sendDeviceCommand(id, 'on'), i * 150);
        });
        addChatMessage('System', '💡 Menyalakan semua perangkat...');
        return true;
    }
    if (msg.includes('mati semua') || msg.includes('matikan semua')) {
        [0, 1, 2, 3, 6, 7, 8].forEach((id, i) => {
            setTimeout(() => sendDeviceCommand(id, 'off'), i * 150);
        });
        addChatMessage('System', '🔌 Mematikan semua perangkat...');
        return true;
    }

    if (msg.includes('lampu utama'))  { handleOnOff(0, msg, 'Lampu Utama'); return true; }
    if (msg.includes('lampu kamar'))  { handleOnOff(1, msg, 'Lampu Kamar'); return true; }
    if (msg.includes('lampu tamu'))   { handleOnOff(2, msg, 'Lampu Tamu');  return true; }

    if (msg.includes('colokan') || msg.includes('terminal')) {
        handleOnOff(3, msg, 'Colokan Terminal'); return true;
    }

    if (msg.includes('kipas')) { handleOnOff(6, msg, 'Kipas'); return true; }

    if (msg.includes('pompa') || msg.includes('siram')) {
        handleOnOff(7, msg, 'Pompa Penyiram'); return true;
    }

    if (msg.includes('valve') || msg.includes('saluran')) {
        handleOnOff(8, msg, 'Solenoid Valve'); return true;
    }

    if (msg.includes('pintu') || msg.includes('kunci')) {
        sendSerialCommand('ON 9');
        addChatMessage('System', '🚪 Membuka pintu (5 detik)...');
        return true;
    }

    if (msg.includes('tirai')) {
        if (msg.includes('buka'))       { sendSerialCommand('TIRAIBUKA 45');  addChatMessage('System', '🪟 Membuka tirai...'); }
        else if (msg.includes('tutup')) { sendSerialCommand('TIRAITUTUP 45'); addChatMessage('System', '🪟 Menutup tirai...'); }
        else if (msg.includes('stop'))  { sendSerialCommand('TIRAIOFF');      addChatMessage('System', '🛑 Menghentikan tirai...'); }
        return true;
    }

    if (msg.includes('ac') || msg.includes('air conditioner')) {
        if (msg.includes('naik'))       { sendSerialCommand('AC_UP');    addChatMessage('System', '🌡️ Menaikkan suhu AC...'); }
        else if (msg.includes('turun')) { sendSerialCommand('AC_DOWN');  addChatMessage('System', '🌡️ Menurunkan suhu AC...'); }
        else                            { sendSerialCommand('AC_POWER'); addChatMessage('System', '❄️ Toggle AC...'); }
        return true;
    }

    return false;
}

function handleOnOff(deviceIndex, msg, deviceName) {
    const isOn   = msg.includes('nyala') || msg.includes('hidup') ||
                   msg.includes('on')    || msg.includes('buka');
    const action = isOn ? 'on' : 'off';
    if (sendDeviceCommand(deviceIndex, action)) {
        addChatMessage('System', `${isOn ? '💡 Menyalakan' : '🔌 Mematikan'} ${deviceName}...`);
    }
}

// =====================================================
// UI HELPERS
// =====================================================
function updateDeviceStatus(device, status) {
    deviceStatus[device] = status;
    const el = document.getElementById(device);
    if (el) {
        el.textContent      = status;
        const isActive      = status.includes('Nyala') || status.includes('Terbuka');
        el.style.color      = isActive ? '#4CAF50' : '#f44336';
        el.style.fontWeight = isActive ? 'bold' : 'normal';
    }
}

function addChatMessage(sender, message) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;

    const div       = document.createElement('div');
    div.className   = sender === 'Anda' ? 'message user' : 'message system';

    const colors = {
        Arduino: '#0066cc',
        Sensor:  '#FF9800',
        System:  '#666',
        Asisten: '#2e7d32'
    };
    if (colors[sender]) {
        div.style.color     = colors[sender];
        div.style.fontSize  = sender === 'Sensor' ? '0.85em' : '';
        div.style.fontStyle = sender === 'Arduino' ? 'italic' : '';
    }

    div.innerHTML = `<strong>${sender}:</strong> ${message}`;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function updateConnectionStatus(connected) {
    const statusItems = document.querySelectorAll('.status-text');
    statusItems.forEach(item => {
        if (!connected && (item.textContent === 'Loading...' || item.textContent === 'Offline')) {
            item.textContent = 'Offline';
            item.style.color = '#ff9800';
        } else if (connected && item.textContent === 'Loading...') {
            item.textContent = 'Mati';
            item.style.color = '#f44336';
        }
    });
}

function toggleMenu() {
    const menu = document.getElementById('hamburgerMenu');
    if (menu) menu.classList.toggle('active');
}

function updateDateTime() {
    const now    = new Date();
    const timeEl = document.querySelector('.time');
    const dateEl = document.querySelector('.date');
    if (timeEl) timeEl.textContent = now.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
    if (dateEl) dateEl.textContent = now.toLocaleDateString('id-ID', { weekday: 'long', year: 'numeric', month: 'numeric', day: 'numeric' });
}

function startVoiceRecognition() {
    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
        addChatMessage('System', '🎤 Browser tidak mendukung pengenalan suara');
        return;
    }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition       = new SpeechRecognition();
    recognition.lang            = 'id-ID';
    recognition.interimResults  = false;
    recognition.maxAlternatives = 1;
    recognition.start();
    addChatMessage('System', '🎤 Mendengarkan...');
    recognition.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        document.getElementById('userInput').value = transcript;
        sendMessage();
    };
    recognition.onerror = () => addChatMessage('System', '🎤 Error pengenalan suara');
}

// =====================================================
// INIT
// =====================================================
window.onload = function () {
    updateDateTime();
    setInterval(updateDateTime, 60000);
    connectToMQTT();
    initTTS();

    // Tambah tombol toggle suara ke area input
    const inputArea = document.querySelector('.input-area');
    if (inputArea) {
        const ttsBtn              = document.createElement('button');
        ttsBtn.id                 = 'ttsToggleBtn';
        ttsBtn.textContent        = '🔊';
        ttsBtn.title              = 'Suara ON (klik untuk mute)';
        ttsBtn.style.backgroundColor = '#4CAF50';
        ttsBtn.style.borderRadius = '50%';
        ttsBtn.style.width        = '40px';
        ttsBtn.style.height       = '40px';
        ttsBtn.style.fontSize     = '18px';
        ttsBtn.style.cursor       = 'pointer';
        ttsBtn.style.border       = 'none';
        ttsBtn.addEventListener('click', toggleTTS);
        inputArea.appendChild(ttsBtn);
    }

    const userInput = document.getElementById('userInput');
    if (userInput) {
        userInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });
        userInput.focus();
        userInput.placeholder = '"nyalakan lampu utama", "buka pintu", atau tanya ke asisten AI...';
    }

    setTimeout(() => {
        addChatMessage('System', '🏠 Selamat datang di Smart Home System!');
        addChatMessage('System', '💬 Ketik perintah langsung atau tanya ke Asisten AI');
        addChatMessage('System', '🔊 Asisten akan berbicara saat membalas — klik 🔊 untuk mute');
        addChatMessage('System', '📋 Ketik "status" untuk cek semua perangkat');
    }, 1500);
};

window.toggleMenu            = toggleMenu;
window.sendMessage           = sendMessage;
window.startVoiceRecognition = startVoiceRecognition;
window.toggleTTS             = toggleTTS;
