import { api } from "./api.js";
import { decryptMessage, encryptMessage } from "./crypto.js";
import { getIdentity } from "./identity.js";

const list = document.querySelector("#message-list");
const template = document.querySelector("#message-template");
const composeForm = document.querySelector("#compose-form");
const composeStatus = document.querySelector("#compose-status");

async function renderMessage(message) {
    const item = template.content.cloneNode(true);
    item.querySelector(".people").textContent = `${message.sender} → ${message.recipient}`;
    item.querySelector(".time").textContent = new Date(`${message.created_at}Z`).toLocaleString();
    try {
        item.querySelector(".body").textContent = await decryptMessage(message, getIdentity());
    } catch {
        item.querySelector(".body").textContent = "This message could not be verified or decrypted.";
    }
    return item;
}

export function clearMessages() {
    list.replaceChildren();
    composeStatus.textContent = "";
}

export async function showBox(box) {
    const result = await api("GET", `/api/messages/${box}`);
    if (result.ok) {
        const items = await Promise.all(result.data.messages.map(renderMessage));
        list.replaceChildren(...items);
    }
}

composeForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const recipient = composeForm.elements.recipient.value;
    const keys = await api("GET", `/api/users/${encodeURIComponent(recipient)}/keys`);
    if (!keys.ok) {
        composeStatus.textContent = keys.data.error;
        return;
    }
    const fields = await encryptMessage(
        composeForm.elements.body.value, getIdentity(), recipient, keys.data.enc_public_key,
    );
    const result = await api("POST", "/api/messages", { recipient, ...fields });
    if (result.ok) {
        composeForm.reset();
        composeStatus.textContent = "Sent.";
        await showBox("outbox");
    } else {
        composeStatus.textContent = result.data.error;
    }
});

document.querySelector("#show-inbox").addEventListener("click", () => showBox("inbox"));
document.querySelector("#show-outbox").addEventListener("click", () => showBox("outbox"));
