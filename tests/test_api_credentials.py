import base64

from helpers import AUTH_TOKEN, KDF_SALT, log_in, sign_up

OTHER_TOKEN = base64.b64encode(b"\x01" * 32).decode()
NOT_BASE64 = "ö" * 24


def test_log_in_wrong_token(client):
    sign_up(client, "alice")

    response = log_in(client, "alice", auth_token=OTHER_TOKEN)

    assert response.status_code == 401
    assert client.get("/api/session").status_code == 401


def test_log_in_unknown_user_looks_like_wrong_token(client):
    sign_up(client, "alice")

    wrong_token = log_in(client, "alice", auth_token=OTHER_TOKEN)
    unknown_user = log_in(client, "no_bob_here", auth_token=OTHER_TOKEN)

    assert unknown_user.status_code == wrong_token.status_code
    assert unknown_user.json == wrong_token.json


def test_log_in_malformed_token(client):
    sign_up(client, "alice")

    assert log_in(client, "alice", auth_token="too short").status_code == 400
    assert log_in(client, "alice", auth_token=NOT_BASE64).status_code == 400


def test_salt_of_known_user(client):
    sign_up(client, "alice")

    response = client.get("/api/users/alice/salt")

    assert response.status_code == 200
    assert response.json["kdf_salt"] == KDF_SALT


def test_fake_salt_is_stable_and_well_formed(client):
    first = client.get("/api/users/no_bob_here/salt")
    second = client.get("/api/users/no_bob_here/salt")

    assert first.status_code == 200
    assert first.json["kdf_salt"] == second.json["kdf_salt"]
    assert len(base64.b64decode(first.json["kdf_salt"], validate=True)) == 16


def test_fake_salt_differs_per_username(client):
    first = client.get("/api/users/no_bob_here/salt")
    second = client.get("/api/users/no_eve_here/salt")

    assert first.json["kdf_salt"] != second.json["kdf_salt"]


def test_sign_up_malformed_credentials(client):
    for kdf_salt, auth_token in [
        ("too short", AUTH_TOKEN),
        (NOT_BASE64, AUTH_TOKEN),
        (KDF_SALT, "too short"),
        (KDF_SALT, NOT_BASE64),
        (None, AUTH_TOKEN),
        (KDF_SALT, None),
    ]:
        response = client.post(
            "/api/users",
            json={"username": "alice", "kdf_salt": kdf_salt, "auth_token": auth_token},
        )
        assert response.status_code == 400
