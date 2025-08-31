// GANTI SEMUA ISI FILE index.js DENGAN KODE INI

// Definisikan alamat backend Anda
const BACKEND_URL = 'https://smarthome-backend-production-1d56.up.railway.app';

function togglePassword() {
    let passwordInput = document.getElementById("password");
    let toggleButton = document.querySelector(".toggle-password");
    let toggleImage = toggleButton.querySelector("img");

    if (passwordInput.type === "password") {
        passwordInput.type = "text";
        toggleImage.src = "./Asset/view.png";
    } else {
        passwordInput.type = "password";
        toggleImage.src = "./Asset/hide.png";
    }
}

function validatePassword() {
    let passwordInput = document.getElementById("password");
    let password = passwordInput.value;

    // Alamat backend yang benar (tanpa /api)
    const url = `${BACKEND_URL}/password`;

    fetch(url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            "password": password
        })
    })
    .then(response => {
        if (response.ok) { // Gunakan response.ok untuk memeriksa status 200-299
            window.location.href = "home.html";
        } else {
            alert('Password salah atau terjadi kesalahan!');
        }
    })
    .catch(error => {
        console.error("Error:", error);
        alert('Tidak dapat terhubung ke server. Periksa koneksi Anda.');
    });
}

document.getElementById("password").addEventListener("keyup", function(event) {
    if (event.key === "Enter") {
        validatePassword();
    }
});
