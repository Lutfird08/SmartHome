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

    const url = `/api/password`;

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
        if (response.status === 200) {
            window.location.href = "home.html";
            return
        }

        alert('wrong password')
    })
    .catch(error => {
        console.log(error)
    })

}

document.getElementById("password").addEventListener("keyup", function(event) {
    if (event.key === "Enter") {
        validatePassword();
    }
});

// let loginCard = document.querySelector(".login-card");
// let submitButton = document.createElement("button");
// submitButton.textContent = "Login";
// submitButton.onclick = validatePassword;
// loginCard.appendChild(submitButton);
