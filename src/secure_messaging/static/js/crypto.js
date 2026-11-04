const encoder = new TextEncoder();

const PBKDF2_ITERATIONS = 600_000;

const ENC_KEY_LABEL = "secure-messaging enc key v1";
const SIGN_KEY_LABEL = "secure-messaging sign key v1";
const MESSAGE_LABEL = "secure-messaging message v1";
const WRAP_LABEL = "secure-messaging wrap v1";


export function toBase64(bytes) {
    return btoa(String.fromCharCode(...bytes));
}

export function fromBase64(text) {
    return Uint8Array.from(atob(text), (char) => char.charCodeAt(0));
}

export function randomBytes(length) {
    return crypto.getRandomValues(new Uint8Array(length));
}

function concatBytes(...arrays) {
    let total = 0;
    for (const array of arrays) {
        total = total + array.length;
    }
    const result = new Uint8Array(total);

    let offset = 0;
    for (const array of arrays) {
        result.set(array, offset);
        offset += array.length;
    }
    return result;
}

function messageContext(sender, recipient) {
    return encoder.encode(`${MESSAGE_LABEL}|${sender}|${recipient}`);
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

async function wrapPrivateKey(privateKey, publicKey, masterKey, label) {
    const iv = randomBytes(12);
    const ciphertext = await crypto.subtle.wrapKey("pkcs8", privateKey, masterKey, {
        name: "AES-GCM", iv, additionalData: concatBytes(encoder.encode(label), fromBase64(publicKey))
    });
    const result = new Uint8Array(iv.length + ciphertext.byteLength);
    result.set(iv);
    result.set(new Uint8Array(ciphertext), iv.length);
    return toBase64(result)
}

function unwrapPrivateKey(wrapped, publicKey, masterKey, label, algorithm, usages) {
    const bytes = fromBase64(wrapped);
    return crypto.subtle.unwrapKey(
        "pkcs8", bytes.slice(12), masterKey,
        { name: "AES-GCM", iv: bytes.slice(0, 12), additionalData: concatBytes(encoder.encode(label), fromBase64(publicKey)) },
        algorithm, false, usages
    );
}

async function exportPublicKey(publicKey) {
     return toBase64(new Uint8Array(await crypto.subtle.exportKey("raw", publicKey)));
}

export async function createIdentity(masterKey) {
    const enc = await crypto.subtle.generateKey({ name: "X25519"}, true, ["deriveKey"]);
    const sign = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]);
    const encPublicKey = await exportPublicKey(enc.publicKey);
    const signPublicKey = await exportPublicKey(sign.publicKey);
    return {
        enc_public_key: await exportPublicKey(enc.publicKey),
        sign_public_key: await exportPublicKey(sign.publicKey),
        wrapped_enc_private_key: await wrapPrivateKey(enc.privateKey, encPublicKey, masterKey, ENC_KEY_LABEL),
        wrapped_sign_private_key: await wrapPrivateKey(sign.privateKey, signPublicKey, masterKey, SIGN_KEY_LABEL),
    };
}

export async function unlockIdentity(keys, masterKey) {
    return {
        encPublicKey: keys.enc_public_key,
        signPublicKey: keys.sign_public_key,
        encPrivateKey: await unwrapPrivateKey(
        keys.wrapped_enc_private_key, keys.enc_public_key, masterKey, ENC_KEY_LABEL, { name: "X25519" }, ["deriveKey"],
        ),
        signPrivateKey: await unwrapPrivateKey(
        keys.wrapped_sign_private_key, keys.sign_public_key, masterKey, SIGN_KEY_LABEL, { name: "Ed25519" }, ["sign"],
        ),
    };
}

async function deriveWrappingKey(privateKey, otherPublic, throwawayPublic, readerPublic) {
    const publicKey = await crypto.subtle.importKey("raw", otherPublic, { name: "X25519" }, false, []);
    const sharedSecretKey = await crypto.subtle.deriveKey(
        { name: "X25519", public: publicKey }, privateKey, "HKDF", false, ["deriveKey"],
    );
    return crypto.subtle.deriveKey(
        {
            name: "HKDF", hash: "SHA-256", salt: new Uint8Array(),
            info: concatBytes(encoder.encode(WRAP_LABEL), throwawayPublic, readerPublic),
        },
        sharedSecretKey, { name: "AES-GCM", length: 256 }, false, ["wrapKey", "unwrapKey"],
    );
}

async function wrapContentKey(contentKey, readerPublicKey, context) {
    const readerPublic = fromBase64(readerPublicKey);
    const throwaway = await crypto.subtle.generateKey({ name: "X25519" }, false, ["deriveKey"]);
    const throwawayPublic = new Uint8Array(await crypto.subtle.exportKey("raw", throwaway.publicKey));
    const wrappingKey = await deriveWrappingKey(throwaway.privateKey, readerPublic, throwawayPublic, readerPublic);
    const iv = randomBytes(12);
    const wrapped = await crypto.subtle.wrapKey("raw", contentKey, wrappingKey, {
        name: "AES-GCM", iv, additionalData: context,
    });
    return toBase64(concatBytes(throwawayPublic, iv, new Uint8Array(wrapped)));
}

async function unwrapContentKey(wrappedKey, identity, context) {
    const bytes = fromBase64(wrappedKey);
    const throwawayPublic = bytes.slice(0, 32);
    const wrappingKey = await deriveWrappingKey(
        identity.encPrivateKey, throwawayPublic, throwawayPublic, fromBase64(identity.encPublicKey),
    );
    return crypto.subtle.unwrapKey(
        "raw", bytes.slice(44), wrappingKey,
        { name: "AES-GCM", iv: bytes.slice(32, 44), additionalData: context },
        { name: "AES-GCM" }, false, ["decrypt"],
    );
}

function signedBytes(sender, recipient, ciphertext, keyForRecipient, keyForSender) {
    return encoder.encode(JSON.stringify(
        [MESSAGE_LABEL, sender, recipient, ciphertext, keyForRecipient, keyForSender],
    ));
}

export async function encryptMessage(text, identity, recipient, recipientEncPublicKey) {
    const context = messageContext(identity.username, recipient);
    const contentKey = await crypto.subtle.generateKey({ name: "AES-GCM", length: 256 }, true, ["encrypt"]);
    const iv = randomBytes(12);
    const encrypted = await crypto.subtle.encrypt(
        { name: "AES-GCM", iv, additionalData: context }, contentKey, encoder.encode(text),
    );
    const ciphertext = toBase64(concatBytes(iv, new Uint8Array(encrypted)));
    const keyForRecipient = await wrapContentKey(contentKey, recipientEncPublicKey, context);
    const keyForSender = await wrapContentKey(contentKey, identity.encPublicKey, context);
    const signature = await crypto.subtle.sign(
        { name: "Ed25519" }, identity.signPrivateKey,
        signedBytes(identity.username, recipient, ciphertext, keyForRecipient, keyForSender),
    );
    return {
        ciphertext,
        key_for_recipient: keyForRecipient,
        key_for_sender: keyForSender,
        signature: toBase64(new Uint8Array(signature)),
    };
}

export async function decryptMessage(message, identity) {
    const signKey = await crypto.subtle.importKey(
        "raw", fromBase64(message.sender_sign_public_key), { name: "Ed25519" }, false, ["verify"],
    );
    const valid = await crypto.subtle.verify(
        { name: "Ed25519" }, signKey, fromBase64(message.signature),
        signedBytes(message.sender, message.recipient, message.ciphertext,
            message.key_for_recipient, message.key_for_sender),
    );
    if (!valid) {
        throw new Error("invalid signature");
    }
    const context = messageContext(message.sender, message.recipient);
    const wrappedKey = message.recipient === identity.username
        ? message.key_for_recipient
        : message.key_for_sender;
    const contentKey = await unwrapContentKey(wrappedKey, identity, context);
    const bytes = fromBase64(message.ciphertext);
    const decrypted = await crypto.subtle.decrypt(
        { name: "AES-GCM", iv: bytes.slice(0, 12), additionalData: context }, contentKey, bytes.slice(12),
    );
    return new TextDecoder().decode(decrypted);
}

export async function keyFingerprint(encPublicKey, signPublicKey) {
    const digest = await crypto.subtle.digest(
        "SHA-256",
        concatBytes(
            encoder.encode("secure-messaging fingerprint v1"),
            fromBase64(encPublicKey),
            fromBase64(signPublicKey),
        ),
    );
    const hex = Array.from(new Uint8Array(digest).slice(0, 16), (byte) =>
        byte.toString(16).padStart(2, "0"),
    ).join("");
    return hex.match(/.{4}/g).join(" ");
}
