import { api } from "./api.js";
import { decryptMessage, encryptMessage, keyFingerprint } from "./crypto.js";
import { getIdentity } from "./identity.js";
import { setPin, getPin, pinChanged } from "./contacts.js";

const list = document.querySelector("#message-list");
const template = document.querySelector("#message-template");
const composeForm = document.querySelector("#compose-form");
const composeStatus = document.querySelector("#compose-status");


async function senderKeyIsTrusted(message, identity) {
    if (message.sender === identity.username) {
        return message.sender_sign_public_key === identity.signPublicKey;
    }
    let pin = getPin(identity.username, message.sender);
    if (pin === null) {
        const keys = await api("GET", `/api/users/${encodeURIComponent(message.sender)}/keys`);
        if (!keys.ok) return false;
        setPin(identity.username, message.sender, keys.data);
        pin = getPin(identity.username, message.sender);
    }
    return pin.sign_public_key === message.sender_sign_public_key;
}

async function renderMessage(message) {
    const item = template.content.cloneNode(true);
    item.querySelector(".people").textContent = `${message.sender} → ${message.recipient}`;
    item.querySelector(".time").textContent = new Date(`${message.created_at}Z`).toLocaleString();
    const body = item.querySelector(".body");
    const identity = getIdentity();
    const warning = item.querySelector(".warning");
    if (!await senderKeyIsTrusted(message, identity)) {
        warning.hidden = false;
        warning.textContent = `${message.sender}'s keys have changed, so this message may not really be from them.`;
    }
    try {
        body.textContent = await decryptMessage(message, identity);
    } catch {
        body.textContent = "This message could not be verified or decrypted.";
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
    const identity = getIdentity();
    const fingerprint = await keyFingerprint(keys.data.enc_public_key, keys.data.sign_public_key);
    const pin = getPin(identity.username, recipient);
    let notice = "Sent.";
    if (pin === null) {
        setPin(identity.username, recipient, keys.data);
        notice = `Sent. First message to ${recipient}: compare this code with them: ${fingerprint}`;
    } else if (pinChanged(pin, keys.data)) {
        const accept = confirm(
            `WARNING: ${recipient}'s keys have changed. Someone may be intercepting. New code: ${fingerprint}. Send anyway?`,
        );
        if (!accept) {
            composeStatus.textContent = "Not sent: keys changed.";
            return;
        }
        setPin(identity.username, recipient, keys.data);
    }
    const fields = await encryptMessage(
        composeForm.elements.body.value, identity, recipient, keys.data.enc_public_key,
    );
    const result = await api("POST", "/api/messages", { recipient, ...fields });
    if (result.ok) {
        composeForm.reset();
        composeStatus.textContent = notice;
        await showBox("outbox");
    } else {
        composeStatus.textContent = result.data.error;
    }
});

document.querySelector("#show-inbox").addEventListener("click", () => showBox("inbox"));
document.querySelector("#show-outbox").addEventListener("click", () => showBox("outbox"));
