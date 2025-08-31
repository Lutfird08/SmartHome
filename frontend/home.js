// GANTI SEMUA ISI FILE home.js DENGAN KODE INI

// Definisikan alamat backend Anda di satu tempat
const BACKEND_URL = 'https://smarthome-backend-production-1d56.up.railway.app';

let recognition;

function toggleMenu() {
    document.getElementById('hamburgerMenu').classList.toggle('active');
}

function postChatWithBot(chat) {
    // Gunakan alamat backend yang benar
    const url = `${BACKEND_URL}/chat-simple`;

    return fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ chat })
    })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            console.log(data.message); // Optional: log success message
            return data; // Return the actual data
        })
        .catch(error => {
            console.error("Error:", error);
            throw error; // Re-throw so caller can handle it
        });
}

function sendMessage() {
    let input = document.getElementById("userInput");
    let message = input.value;
    if (message.trim() !== "") {
        addMessage(message, "user-message");
        processCommand(message);
        input.value = "";
        if (recognition) {
            recognition.stop();
        }
    }
}

function addMessage(text, className) {
    let chatMessages = document.getElementById("chatMessages");
    let messageElement = document.createElement("div");
    messageElement.classList.add("message", className);
    messageElement.textContent = text;
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

async function processCommand(command) {
    try {
        const response = await postChatWithBot(command);
        setTimeout(() => addMessage(response.response, "assistant-message"), 1000);
    } catch (error) {
        addMessage("Maaf, terjadi kesalahan saat menghubungi asisten.", "assistant-message");
    }
}

function startVoiceRecognition() {
    if ('webkitSpeechRecognition' in window) {
        recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'id-ID';

        recognition.onstart = function () {
            document.getElementById("userInput").placeholder = "Mendengarkan...";
            document.querySelector('.input-area button:last-child').classList.add('active');
        };

        recognition.onresult = function (event) {
            var transcript = event.results[0][0].transcript;
            document.getElementById("userInput").value = transcript;
            sendMessage();
        };

        recognition.onerror = function (event) {
            console.error('Speech recognition error:', event.error);
            document.getElementById("userInput").placeholder = "Masukkan Perintah...";
            document.querySelector('.input-area button:last-child').classList.remove('active');
        };

        recognition.onend = function () {
            document.getElementById("userInput").placeholder = "Masukkan Perintah...";
            document.querySelector('.input-area button:last-child').classList.remove('active');
        };

        recognition.start();
    } else {
        alert("Maaf, browser Anda tidak mendukung pengenalan suara.");
    }
}

function updateDateTime() {
    const now = new Date();
    const timeElement = document.querySelector('.time');
    const dateElement = document.querySelector('.date');

    timeElement.textContent = now.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
    dateElement.textContent = now.toLocaleDateString('id-ID', { weekday: 'long', year: 'numeric', month: '2-digit', day: '2-digit' });
}

setInterval(updateDateTime, 1000);
updateDateTime();

async function updateStatus() {
    try {
        // Fetch lamp status dengan alamat backend yang benar
        const lampResponse = await fetch(`${BACKEND_URL}/api/lamp/one`);
        const lampData = await lampResponse.json();
        document.querySelector('#lamp').textContent = lampData.condition ? 'Aktif' : 'Nonaktif';

        // Fetch AC status dengan alamat backend yang benar
        const acResponse = await fetch(`${BACKEND_URL}/api/ac`);
        const acData = await acResponse.json();
        document.querySelector('#ac').textContent = acData.condition ? 'Aktif' : 'Nonaktif';

        // Fetch door lock status dengan alamat backend yang benar
        const doorResponse = await fetch(`${BACKEND_URL}/api/door`);
        const doorData = await doorResponse.json();
        document.querySelector('#door').textContent = doorData.condition ? 'Aktif' : 'Nonaktif';

    } catch (error) {
        console.error('Error fetching status:', error);
    }
}

// Panggil updateStatus saat skrip dimuat dan setiap beberapa detik
updateStatus();
setInterval(updateStatus, 5000); // Diubah menjadi 5 detik agar tidak terlalu sering
