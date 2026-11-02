let current = null;

export function setIdentity(identity) {
    current = identity;
}

export function getIdentity() {
    return current;
}
