import base64

from secure_messaging.models import Message, User

KDF_SALT = base64.b64encode(bytes(16)).decode()
AUTH_TOKEN = base64.b64encode(bytes(32)).decode()
ENC_PUBLIC_KEY = base64.b64encode(b"\x01" * 32).decode()
SIGN_PUBLIC_KEY = base64.b64encode(b"\x02" * 32).decode()
WRAPPED_ENC_PRIVATE_KEY = base64.b64encode(b"\x03" * 76).decode()
WRAPPED_SIGN_PRIVATE_KEY = base64.b64encode(b"\x04" * 76).decode()
CIPHERTEXT = base64.b64encode(b"\x05" * 40).decode()
KEY_FOR_RECIPIENT = base64.b64encode(b"\x06" * 92).decode()
KEY_FOR_SENDER = base64.b64encode(b"\x07" * 92).decode()
SIGNATURE = base64.b64encode(b"\x08" * 64).decode()


def sign_up(
    client,
    username,
    kdf_salt=KDF_SALT,
    auth_token=AUTH_TOKEN,
    enc_public_key=ENC_PUBLIC_KEY,
    sign_public_key=SIGN_PUBLIC_KEY,
    wrapped_enc_private_key=WRAPPED_ENC_PRIVATE_KEY,
    wrapped_sign_private_key=WRAPPED_SIGN_PRIVATE_KEY,
):
    return client.post(
        "/api/users",
        json={
            "username": username,
            "kdf_salt": kdf_salt,
            "auth_token": auth_token,
            "enc_public_key": enc_public_key,
            "sign_public_key": sign_public_key,
            "wrapped_enc_private_key": wrapped_enc_private_key,
            "wrapped_sign_private_key": wrapped_sign_private_key,
        },
    )


def log_in(client, username, auth_token=AUTH_TOKEN):
    return client.post("/api/session", json={"username": username, "auth_token": auth_token})


def make_db_user(username):
    return User(
        username=username,
        password_hash="x",
        kdf_salt=KDF_SALT,
        enc_public_key=ENC_PUBLIC_KEY,
        sign_public_key=SIGN_PUBLIC_KEY,
        wrapped_enc_private_key=WRAPPED_ENC_PRIVATE_KEY,
        wrapped_sign_private_key=WRAPPED_SIGN_PRIVATE_KEY,
    )


def make_db_message(sender_id, recipient_id):
    return Message(
        sender_id=sender_id,
        recipient_id=recipient_id,
        ciphertext=CIPHERTEXT,
        key_for_recipient=KEY_FOR_RECIPIENT,
        key_for_sender=KEY_FOR_SENDER,
        signature=SIGNATURE,
    )


def send(
    client,
    recipient,
    ciphertext=CIPHERTEXT,
    key_for_recipient=KEY_FOR_RECIPIENT,
    key_for_sender=KEY_FOR_SENDER,
    signature=SIGNATURE,
):
    return client.post(
        "/api/messages",
        json={
            "recipient": recipient,
            "ciphertext": ciphertext,
            "key_for_recipient": key_for_recipient,
            "key_for_sender": key_for_sender,
            "signature": signature,
        },
    )
