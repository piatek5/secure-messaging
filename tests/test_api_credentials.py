import base64

import pytest
from helpers import (
    AUTH_TOKEN,
    ENC_PUBLIC_KEY,
    KDF_SALT,
    SIGN_PUBLIC_KEY,
    WRAPPED_ENC_PRIVATE_KEY,
    WRAPPED_SIGN_PRIVATE_KEY,
    log_in,
    sign_up,
)

OTHER_TOKEN = base64.b64encode(b"\x01" * 32).decode()
NOT_BASE64 = "ö" * 24


def to_base64(length):
    return base64.b64encode(bytes(length)).decode()


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
        response = sign_up(client, username="alice", kdf_salt=kdf_salt, auth_token=auth_token)

        assert response.status_code == 400


@pytest.mark.parametrize(
    "field",
    [
        "enc_public_key",
        "sign_public_key",
        "wrapped_enc_private_key",
        "wrapped_sign_private_key",
    ],
)
@pytest.mark.parametrize("bad_value", ["", "not base64!", NOT_BASE64, None])
def test_sign_up_malformed_key(client, field, bad_value):
    response = sign_up(client, "alice", **{field: bad_value})

    assert response.status_code == 400


def test_sign_up_public_key_wrong_length(client):
    for length in [31, 33]:
        response = sign_up(client, "alice", enc_public_key=to_base64(length))
        assert response.status_code == 400

        response = sign_up(client, "alice", sign_public_key=to_base64(length))
        assert response.status_code == 400


def test_sign_up_wrapped_key_too_big(client):
    response = sign_up(client, "alice", wrapped_enc_private_key=to_base64(257))
    assert response.status_code == 400

    response = sign_up(client, "alice", wrapped_sign_private_key=to_base64(257))
    assert response.status_code == 400


def test_sign_up_wrapped_key_largest_allowed(client):
    response = sign_up(client, "alice", wrapped_enc_private_key=to_base64(256))
    assert response.status_code == 201

    response = sign_up(client, "bob", wrapped_sign_private_key=to_base64(256))
    assert response.status_code == 201


def test_login_keys(client):
    sign_up(client, username="alice")
    response = log_in(client, username="alice")

    assert response.status_code == 200
    assert response.json["enc_public_key"] == ENC_PUBLIC_KEY
    assert response.json["sign_public_key"] == SIGN_PUBLIC_KEY
    assert response.json["wrapped_enc_private_key"] == WRAPPED_ENC_PRIVATE_KEY
    assert response.json["wrapped_sign_private_key"] == WRAPPED_SIGN_PRIVATE_KEY


def test_failed_login_returns_no_keys(client):
    sign_up(client, username="alice")

    response = log_in(client, username="alice", auth_token=OTHER_TOKEN)

    assert response.status_code == 401
    assert "enc_public_key" not in response.json
    assert "sign_public_key" not in response.json
    assert "wrapped_sign_private_key" not in response.json
    assert "wrapped_sign_private_key" not in response.json


def test_public_keys_require_login(client):
    sign_up(client, username="alice")

    response = client.get("/api/users/alice/keys")

    assert response.status_code == 401


def test_public_keys_of_unknown_user(client):
    sign_up(client, username="alice")
    log_in(client, username="alice")

    response = client.get("/api/users/no_bob_here/keys")

    assert response.status_code == 404


def test_public_keys_contain_nothing_else(client):
    sign_up(client, username="alice")
    sign_up(client, username="bob")
    log_in(client, username="alice")

    response = client.get("/api/users/bob/keys")

    assert response.status_code == 200
    assert response.json == {
        "enc_public_key": ENC_PUBLIC_KEY,
        "sign_public_key": SIGN_PUBLIC_KEY,
    }
