const encoder = new TextEncoder();
const PBKDF2_ITERATIONS = 600_000;

export function toBase64(bytes) {
    return btoa(String.fromCharCode(...bytes))
}

export function fromBase64(text) {
  return Uint8Array.from(atob(text), (char) => char.charCodeAt(0));
}

export function randomBytes(length) {
  return crypto.getRandomValues(new Uint8Array(length));
}

export async function deriveKeys(password, salt) {
    const passwordKey = await crypto.subtle.importKey(
        "raw", encoder.encode(password.normalize("NKFC")), "PBKDF2", false, ["deriveBits"]
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
