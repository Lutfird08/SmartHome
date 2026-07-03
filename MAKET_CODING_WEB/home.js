// Konfigurasi MQTT
const MQTT_BROKER_URL = 'wss://broker.emqx.io:8084/mqtt';
const MQTT_TOPIC_PREFIX = 'smart_home/';

// Variabel global
let mqttClient = null;
let isConnected = false;

// =====================================================
// MAPPING PERINTAH — sesuai Arduino Mega
// buttonNames[]: lampu_utama(0), lampu_kamar(1), lampu_tamu(2),
//                colokan_terminal(3), tirai_tutup(4), tirai_buka(5),
//                kipas(6), pompa_penyiram(7), solenoid_valve(8), solenoid_door(9)
// =====================================================
const deviceCommands = {
    0:  { on: 'ON 0',       off: 'OFF 0'    }, // Lampu Utama
    1:  { on: 'ON 1',       off: 'OFF 1'    }, // Lampu Kamar
    2:  { on: 'ON 2',       off: 'OFF 2'    }, // Lampu Tamu
    3:  { on: 'ON 3',       off: 'OFF 3'    }, // Colokan Terminal
    6:  { on: 'KIPASON 50', off: 'KIPASOFF' }, // Kipas
    7:  { on: 'ON 7',       off: 'OFF 7'    }, // Pompa Penyiram
    8:  { on: 'ON 8',       off: 'OFF 8'    }, // Solenoid Valve
    9:  { on: 'ON 9',       off: 'OFF 9'    }, // Solenoid Door (timer di Arduino)

    // AC — pakai relay IR, bukan index ON/OFF biasa
    'ac_power': 'AC_POWER',
    'ac_up':    'AC_UP',
    'ac_down':  'AC_DOWN',

    // Tirai — motor L298N
    'tirai_buka':  'TIRAIBUKA 45',
    'tirai_tutup': 'TIRAITUTUP 45',
    'tirai_stop':  'TIRAIOFF'
};

// Nama perangkat
const deviceNames = {
    0: 'lampu_utama',
    1: 'lampu_kamar',
    2: 'lampu_tamu',
    3: 'colokan_terminal',
    4: 'tirai_tutup',
    5: 'tirai_buka',
    6: 'kipas',
    7: 'pompa_penyiram',
    8: 'solenoid_valve',
    9: 'solenoid_door'
};

// Status perangkat untuk UI home
let deviceStatus = {
    lamp: 'Mati',
    ac:   'Mati',
    door: 'Terkunci'
};

// Status semua perangkat
let allDeviceStatus = {
    0: false, 1: false, 2: false, 3: false,
    6: false, 7: false, 8: false, 9: false,
    ac: false
};

// =====================================================
// MQTT
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
    });

    mqttClient.on('message', (topic, message) => {
        handleIncomingMessage(topic, message.toString());
    });

    mqttClient.on('error', () => {
        updateConnectionStatus(false);
    });

    mqttClient.on('close', () => {
        isConnected = false;
        updateConnectionStatus(false);
    });
}

function subscribeToTopics() {
    ['response', 'status', 'sensor'].forEach(t => {
        mqttClient.subscribe(MQTT_TOPIC_PREFIX + t, { qos: 0 });
    });
}

// =====================================================
// HANDLE PESAN MASUK
// =====================================================
function handleIncomingMessage(topic, message) {
    if (message.includes("SISTEM KONTROL RUMAH") ||
        message.includes("PERINTAH SERIAL:") ||
        message.includes("Catatan:") ||
        message.startsWith("ARDUINO_MEGA:") ||
        message.startsWith("ESP32:")) return;

    if (topic.includes('status') || topic.includes('response')) {
        parseArduinoResponse(message);
    } else if (topic.includes('sensor')) {
        processSensorData(message);
    }
}

function parseArduinoResponse(message) {
    if (!message.includes(':')) return;

    const parts = message.split(':');
    if (parts.length < 2) return;

    const deviceName = parts[0].trim().toLowerCase();
    const status     = parts[1].trim().toUpperCase();
    const isOn       = status.includes('ON') || status.includes('AKTIF') || status.includes('NYALA');

    addChatMessage('Arduino', `${parts[0].trim()}: ${parts[1].trim()}`);

    // Update status berdasarkan nama device dari Arduino
    switch (deviceName) {
        case 'lampu_utama':
            allDeviceStatus[0] = isOn;
            updateDeviceStatus('lamp', isOn ? 'Nyala' : 'Mati');
            break;
        case 'lampu_kamar':   allDeviceStatus[1] = isOn; break;
        case 'lampu_tamu':    allDeviceStatus[2] = isOn; break;
        case 'colokan_terminal': allDeviceStatus[3] = isOn; break;
        case 'kipas':         allDeviceStatus[6] = isOn; break;
        case 'pompa_penyiram': allDeviceStatus[7] = isOn; break;
        case 'solenoid_valve': allDeviceStatus[8] = isOn; break;
        case 'solenoid_door':
            allDeviceStatus[9] = isOn;
            updateDeviceStatus('door', isOn ? 'Terbuka' : 'Terkunci');
            break;

        // AC — konfirmasi pulse dari relay IR
        case 'ac_power':
            allDeviceStatus.ac = !allDeviceStatus.ac; // toggle
            updateDeviceStatus('ac', allDeviceStatus.ac ? 'Nyala' : 'Mati');
            break;

        case 'tirai':
            addChatMessage('System', `Tirai: ${parts[1].trim()}`);
            break;
    }
}

function processSensorData(message) {
    // Format dari Arduino: "ldr:nilai", "soil:nilai", "humidity:nilai", "temperature:nilai"
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
    mqttClient.publish(MQTT_TOPIC_PREFIX + 'control', command, { qos: 0 });
    return true;
}

function sendDeviceCommand(deviceIndex, action) {
    const cmd = deviceCommands[deviceIndex];
    if (!cmd) {
        addChatMessage('System', `Perangkat index ${deviceIndex} tidak dikenali`);
        return false;
    }
    const command = cmd[action];
    if (!command) {
        addChatMessage('System', `Perintah '${action}' tidak tersedia untuk perangkat ini`);
        return false;
    }
    return sendSerialCommand(command);
}

// =====================================================
// CHAT — PROSES PERINTAH
// =====================================================
function sendMessage() {
    const input = document.getElementById('userInput');
    const message = input.value.trim();
    if (message === '') return;

    addChatMessage('Anda', message);
    processCommand(message);
    input.value = '';
}

function processCommand(message) {
    const msg = message.toLowerCase().trim();

    // STATUS
    if (msg === 'status') {
        sendSerialCommand('STATUS');
        addChatMessage('System', '📋 Meminta status sistem...');
        return;
    }

    // SEMUA
    if (msg.includes('nyala semua') || msg.includes('nyalakan semua')) {
        [0, 1, 2, 3, 6, 7, 8].forEach((id, i) => {
            setTimeout(() => sendDeviceCommand(id, 'on'), i * 150);
        });
        addChatMessage('System', '💡 Menyalakan semua perangkat...');
        return;
    }
    if (msg.includes('mati semua') || msg.includes('matikan semua')) {
        [0, 1, 2, 3, 6, 7, 8].forEach((id, i) => {
            setTimeout(() => sendDeviceCommand(id, 'off'), i * 150);
        });
        addChatMessage('System', '🔌 Mematikan semua perangkat...');
        return;
    }

    // LAMPU
    if (msg.includes('lampu utama'))    { handleOnOff(0, msg, 'Lampu Utama'); return; }
    if (msg.includes('lampu kamar'))    { handleOnOff(1, msg, 'Lampu Kamar'); return; }
    if (msg.includes('lampu tamu'))     { handleOnOff(2, msg, 'Lampu Tamu'); return; }

    // COLOKAN / TERMINAL
    if (msg.includes('colokan') || msg.includes('terminal')) {
        handleOnOff(3, msg, 'Colokan Terminal'); return;
    }

    // KIPAS
    if (msg.includes('kipas')) {
        handleOnOff(6, msg, 'Kipas'); return;
    }

    // POMPA
    if (msg.includes('pompa') || msg.includes('siram')) {
        handleOnOff(7, msg, 'Pompa Penyiram'); return;
    }

    // SOLENOID VALVE
    if (msg.includes('valve')) {
        handleOnOff(8, msg, 'Solenoid Valve'); return;
    }

    // PINTU / SOLENOID DOOR
    if (msg.includes('pintu') || msg.includes('solenoid door')) {
        sendDeviceCommand(9, 'on'); // Arduino auto-off setelah 5 detik
        addChatMessage('System', '🚪 Membuka pintu (5 detik)...');
        return;
    }

    // TIRAI
    if (msg.includes('tirai')) {
        if (msg.includes('buka'))        { sendSerialCommand('TIRAIBUKA 45');  addChatMessage('System', '🪟 Membuka tirai...'); }
        else if (msg.includes('tutup'))  { sendSerialCommand('TIRAITUTUP 45'); addChatMessage('System', '🪟 Menutup tirai...'); }
        else if (msg.includes('stop') || msg.includes('berhenti')) {
            sendSerialCommand('TIRAIOFF'); addChatMessage('System', '🛑 Menghentikan tirai...');
        }
        return;
    }

    // AC
    if (msg.includes('ac') || msg.includes('air conditioner') || msg.includes('pendingin')) {
        if (msg.includes('naik') || msg.includes('naikkan')) {
            sendSerialCommand('AC_UP');
            addChatMessage('System', '🌡️ Menaikkan suhu AC...');
        } else if (msg.includes('turun') || msg.includes('turunkan')) {
            sendSerialCommand('AC_DOWN');
            addChatMessage('System', '🌡️ Menurunkan suhu AC...');
        } else {
            // on/off = toggle power
            sendSerialCommand('AC_POWER');
            addChatMessage('System', '❄️ Toggle AC...');
        }
        return;
    }

    // Fallback: kirim langsung sebagai raw command
    sendSerialCommand(message.toUpperCase());
}

// Helper on/off berdasarkan kata kunci
function handleOnOff(deviceIndex, msg, deviceName) {
    const isOn = msg.includes('nyala') || msg.includes('hidup') || msg.includes('on') || msg.includes('buka');
    const action = isOn ? 'on' : 'off';
    if (sendDeviceCommand(deviceIndex, action)) {
        addChatMessage('System', `${isOn ? 'Menyalakan' : 'Mematikan'} ${deviceName}...`);
    }
}

// =====================================================
// UI HELPERS
// =====================================================
function updateDeviceStatus(device, status) {
    deviceStatus[device] = status;
    const el = document.getElementById(device);
    if (el) {
        el.textContent = status;
        const isActive = status.includes('Nyala') || status.includes('Terbuka');
        el.style.color = isActive ? '#4CAF50' : '#f44336';
        el.style.fontWeight = isActive ? 'bold' : 'normal';
    }
}

function addChatMessage(sender, message) {
    const chatMessages = document.getElementById('chatMessages');
    if (!chatMessages) return;

    const div = document.createElement('div');
    div.className = sender === 'Anda' ? 'message user' : 'message system';

    const colors = { Arduino: '#0066cc', Sensor: '#FF9800', System: '#666' };
    if (colors[sender]) {
        div.style.color = colors[sender];
        div.style.fontSize = sender !== 'Arduino' ? '0.9em' : '';
        div.style.fontStyle = sender === 'Arduino' ? 'italic' : '';
    }

    div.innerHTML = `<strong>${sender}:</strong> ${message}`;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function updateConnectionStatus(connected) {
    const statusItems = document.querySelectorAll('.status-text');
    statusItems.forEach(item => {
        if (!connected) {
            item.textContent = 'Offline';
            item.style.color = '#ff9800';
        } else if (item.textContent === 'Offline' || item.textContent === 'Loading...') {
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
    const now = new Date();
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
    const recognition = new SpeechRecognition();
    recognition.lang = 'id-ID';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.start();
    recognition.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        document.getElementById('userInput').value = transcript;
        sendMessage();
    };
    recognition.onerror = () => addChatMessage('System', '🎤 Error dalam pengenalan suara');
}

// =====================================================
// INIT
// =====================================================
window.onload = function() {
    updateDateTime();
    setInterval(updateDateTime, 60000);
    connectToMQTT();

    const userInput = document.getElementById('userInput');
    if (userInput) {
        userInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });
        userInput.focus();
        userInput.placeholder = 'Contoh: "nyalakan lampu utama", "matikan kipas", "buka tirai"';
    }

    setTimeout(() => {
        addChatMessage('System', '🏠 Selamat datang di Smart Home System!');
        addChatMessage('System', '💬 Perintah: "nyalakan lampu utama", "matikan kipas", "buka pintu", "tirai buka"');
        addChatMessage('System', '🎤 Klik ikon mikrofon untuk perintah suara');
        addChatMessage('System', '📋 Ketik "status" untuk melihat status semua perangkat');
    }, 1500);
};

window.toggleMenu = toggleMenu;
window.sendMessage = sendMessage;
window.startVoiceRecognition = startVoiceRecognition;