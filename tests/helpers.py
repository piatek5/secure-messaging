import base64

from secure_messaging.models import User

KDF_SALT = base64.b64encode(bytes(16)).decode()
AUTH_TOKEN = base64.b64encode(bytes(32)).decode()


def sign_up(client, username):
    return client.post(
        "/api/users",
        json={"username": username, "kdf_salt": KDF_SALT, "auth_token": AUTH_TOKEN},
    )


def log_in(client, username, auth_token=AUTH_TOKEN):
    return client.post("/api/session", json={"username": username, "auth_token": auth_token})


def make_db_user(username):
    return User(username=username, password_hash="x", kdf_salt="x")
