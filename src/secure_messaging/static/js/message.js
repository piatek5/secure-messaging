import { api } from "./api.js";

const list = document.querySelector("#message-list");
const template = document.querySelector("#message-template");
const composeForm = document.querySelector("#compose-form");
const composeStatus = document.querySelector("#compose-status");

function renderMessage(message) {
    const item = template.content.cloneNode(true)
    item.querySelector(".people").textContent = `${message.sender} → ${message.recipient}`;
    item.querySelector(".time").textContent = new Date(`${message.created_at}Z`).toLocaleString();
    item.querySelector(".body").textContent = message.body;
    return item;
}

export function clearMessages() {
    list.replaceChildren();
    composeStatus.textContent = "";
}

export async function showBox(box) {
    const result = await api("GET", `/api/messages/${box}`);
    if (result.ok) {
        list.replaceChildren(...result.data.messages.map(renderMessage));
    }
}

composeForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const result = await api("POST", "/api/messages", {
        recipient: composeForm.elements.recipient.value,
        body: composeForm.elements.body.value,
    });
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
