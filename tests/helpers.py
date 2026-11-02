import base64

from secure_messaging.models import User

KDF_SALT = base64.b64encode(bytes(16)).decode()
AUTH_TOKEN = base64.b64encode(bytes(32)).decode()
ENC_PUBLIC_KEY = base64.b64encode(bytes(32)).decode()
SIGN_PUBLIC_KEY = base64.b64encode(bytes(32)).decode()
WRAPPED_ENC_PRIVATE_KEY = base64.b64encode(bytes(76)).decode()
WRAPPED_SIGN_PRIVATE_KEY = base64.b64encode(bytes(76)).decode()


def sign_up(client, username, 
    kdf_salt=KDF_SALT,
    auth_token=AUTH_TOKEN,
    enc_public_key=ENC_PUBLIC_KEY,
    sign_public_key=SIGN_PUBLIC_KEY,
    wrapped_enc_private_key=WRAPPED_ENC_PRIVATE_KEY,
    wrapped_sign_private_key=WRAPPED_SIGN_PRIVATE_KEY
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
        kdf_salt="x",
        enc_public_key="x",
        sign_public_key="x",
        wrapped_enc_private_key="x",
        wrapped_sign_private_key="x",
    )
