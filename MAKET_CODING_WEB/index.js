// Password yang valid (bisa diganti sesuai kebutuhan)
const VALID_PASSWORD = "lutfi123";

function togglePassword() {
    let passwordInput = document.getElementById("password");
    let toggleButton = document.querySelector(".toggle-password");
    let toggleImage = toggleButton.querySelector("img");

    if (passwordInput.type === "password") {
        passwordInput.type = "text";
        toggleImage.src = "Asset/view.png";
    } else {
        passwordInput.type = "password";
        toggleImage.src = "Asset/hide.png";
    }
}

function validatePassword() {
    let passwordInput = document.getElementById("password");
    let password = passwordInput.value.trim();

    // Validasi langsung di frontend
    if (password === VALID_PASSWORD) {
        // Redirect ke halaman home (atau halaman lain)
        window.location.href = "home.html"; // Ganti dengan halaman tujuan
    } else {
        alert('Password salah! Silakan coba lagi.');
        passwordInput.value = ""; // Kosongkan input
        passwordInput.focus(); // Fokus kembali ke input
    }
}

// Event listener untuk tombol Enter
document.getElementById("password").addEventListener("keyup", function(event) {
    if (event.key === "Enter") {
        validatePassword();
    }
});