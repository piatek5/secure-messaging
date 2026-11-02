const encoder = new TextEncoder();
const PBKDF2_ITERATIONS = 600_000;
const ENC_KEY_LABEL = "secure-messaging enc key v1";
const SIGN_KEY_LABEL = "secure-messaging sign key v1";

export function toBase64(bytes) {
    return btoa(String.fromCharCode(...bytes));
}

export function fromBase64(text) {
    return Uint8Array.from(atob(text), (char) => char.charCodeAt(0));
}

export function randomBytes(length) {
    return crypto.getRandomValues(new Uint8Array(length));
}

export async function deriveKeys(password, salt) {
    const passwordKey = await crypto.subtle.importKey(
        "raw", encoder.encode(password.normalize("NFKC")), "PBKDF2", false, ["deriveBits"]
    );
    const baseBits = await crypto.subtle.deriveBits(
        { name: "PBKDF2", hash: "SHA-256", salt, iterations: PBKDF2_ITERATIONS }, passwordKey, 256
    );
    const baseKey = await crypto.subtle.importKey(
        "raw", baseBits, "HKDF", false, ["deriveBits", "deriveKey"]
    );

    const hkdf = (label) => ({
        name: "HKDF", hash: "SHA-256", salt: new Uint8Array(), info: encoder.encode(label)
    });
    const tokenBits = await crypto.subtle.deriveBits(
        hkdf("secure-messaging auth v1"),
        baseKey, 256);
    const masterKey = await crypto.subtle.deriveKey(
        hkdf("secure-messaging master v1"), baseKey,
        { name: "AES-GCM", length: 256 }, false, ["wrapKey", "unwrapKey"],
    );

    return { authToken: toBase64(new Uint8Array(tokenBits)), masterKey };
}

async function wrapPrivateKey(privateKey, masterKey, label) {
    const iv = randomBytes(12);
    const ciphertext = await crypto.subtle.wrapKey("pkcs8", privateKey, masterKey, {
        name: "AES-GCM", iv, additionalData: encoder.encode(label)
    });
    const result = new Uint8Array(iv.length + ciphertext.byteLength);
    result.set(iv);
    result.set(new Uint8Array(ciphertext), iv.length);
    return toBase64(result)
}

function unwrapPrivateKey(wrapped, masterKey, label, algorithm, usages) {
    const bytes = fromBase64(wrapped);
    return crypto.subtle.unwrapKey(
        "pkcs8", bytes.slice(12), masterKey,
        { name: "AES-GCM", iv: bytes.slice(0, 12), additionalData: encoder.encode(label) },
        algorithm, false, usages
    );
}

async function exportPublicKey(publicKey) {
     return toBase64(new Uint8Array(await crypto.subtle.exportKey("raw", publicKey)));
}

export async function createIdentity(masterKey) {
    const enc = await crypto.subtle.generateKey({ name: "X25519"}, true, ["deriveBits"]);
    const sign = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
    return {
        enc_public_key: await exportPublicKey(enc.publicKey),
        sign_public_key: await exportPublicKey(sign.publicKey),
        wrapped_enc_private_key: await wrapPrivateKey(enc.privateKey, masterKey, ENC_KEY_LABEL),
        wrapped_sign_private_key: await wrapPrivateKey(sign.privateKey, masterKey, SIGN_KEY_LABEL),
    };
}

export async function unlockIdentity(keys, masterKey) {
    return {
        encPublicKey: keys.enc_public_key,
        signPublicKey: keys.sign_public_key,
        encPrivateKey: await unwrapPrivateKey(
        keys.wrapped_enc_private_key, masterKey, ENC_KEY_LABEL, { name: "X25519" }, ["deriveBits"],
        ),
        signPrivateKey: await unwrapPrivateKey(
        keys.wrapped_sign_private_key, masterKey, SIGN_KEY_LABEL, { name: "Ed25519" }, ["sign"],
        ),
    };
}
