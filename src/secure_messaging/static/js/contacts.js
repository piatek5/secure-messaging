function pinKey(owner, contact) {
    return `secure-messaging:pin:${owner}:${contact}`;
}

export function getPin(owner, contact) {
    const stored = localStorage.getItem(pinKey(owner, contact));
    return stored === null ? null : JSON.parse(stored);
}

export function setPin(owner, contact, keys) {
    localStorage.setItem(pinKey(owner, contact), JSON.stringify({
        enc_public_key: keys.enc_public_key,
        sign_public_key: keys.sign_public_key,
    }));
}

export function pinChanged(pin, keys) {
    return pin.enc_public_key !== keys.enc_public_key
        || pin.sign_public_key !== keys.sign_public_key;
}
