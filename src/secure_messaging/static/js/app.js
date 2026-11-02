import { api } from "./api.js"

const authView = document.querySelector("#auth-view");
const mainView = document.querySelector("#main-view");
const authForm = document.querySelector("#auth-form");
const usernameInput = document.querySelector("#username");
const authError = document.querySelector("#auth-error");

function showAuth() {
    mainView.hidden = true;
    authView.hidden = false;
    usernameInput.focus();
}

function showMain(user) {
    document.querySelector("#current-user").textContent = user.username;
    authView.hidden = true;
    mainView.hidden = false;
}

async function logIn() {
    const result = await api("POST", "/api/session", { username: usernameInput.value });
    if (result.ok) {
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
    const result = await api("POST", "/api/users", { username: usernameInput.value });
    if (result.ok) {
        await logIn();
    } else {
        authError.textContent = result.data.error;
    }
});

document.querySelector("#logout-button").addEventListener("click", async () =>{
    await api("DELETE", "/api/session");
    showAuth();
});

// On page load check if we are still logged in
const session = await api("GET", "/api/session");
if (session.ok) {
    showMain(session.data);
} else {
    showAuth();
}
