import { api } from "./api.js"
import { clearMessages, showBox } from "./message.js";
import { deriveKeys, fromBase64, randomBytes, toBase64 } from "./crypto.js";

const authView = document.querySelector("#auth-view");
const mainView = document.querySelector("#main-view");
const authForm = document.querySelector("#auth-form");
const usernameInput = document.querySelector("#username");
const authError = document.querySelector("#auth-error");
const passwordInput = document.querySelector("#password");

function showAuth() {
    mainView.hidden = true;
    authView.hidden = false;
    usernameInput.focus();
}

function showMain(user) {
    document.querySelector("#current-user").textContent = user.username;
    authView.hidden = true;
    mainView.hidden = false;
    showBox("inbox");
}

let masterKey = null;

async function logIn() {
    const username = usernameInput.value;
    const salt = await api("GET", `/api/users/${encodeURIComponent(username)}/salt`);
    if (!salt.ok) {
        authError.textContent = salt.data.error;
        return;
    }
    const keys = await deriveKeys(passwordInput.value, fromBase64(salt.data.kdf_salt));
    const result = await api("POST", "/api/session", { username, auth_token: keys.authToken });
    if (result.ok) {
        masterKey = keys.masterKey;
        passwordInput.value = "";
        authError.textContent = "";
        showMain(result.data);
    } else {
        authError.textContent = result.data.error;
    }
}

authForm.addEventListener("submit", async (event) => {
    event.preventDefault()
    await logIn();
});

document.querySelector("#signup-button").addEventListener("click", async () => {
    if (!authForm.reportValidity()) return;
    const salt = randomBytes(16);
    const { authToken } = await deriveKeys(passwordInput.value, salt);
    const result = await api("POST", "/api/users", {
        username: usernameInput.value, kdf_salt: toBase64(salt), auth_token: authToken,
    });
    if (result.ok) {
        await logIn();
    } else {
        authError.textContent = result.data.error;
    }
});

document.querySelector("#logout-button").addEventListener("click", async () =>{
    await api("DELETE", "/api/session");
    clearMessages();
    masterKey = null;
    showAuth();
});

// On page load check if the session is still valid
const session = await api("GET", "/api/session");
showAuth();
if (session.ok) {
    usernameInput.value = session.data.username;
    authError.textContent = "Enter your password to unlock.";
    passwordInput.focus();
}
