import base64

from helpers import (
    CIPHERTEXT,
    KEY_FOR_RECIPIENT,
    KEY_FOR_SENDER,
    SIGN_PUBLIC_KEY,
    SIGNATURE,
    log_in,
    send,
    sign_up,
)

MAX_CIPHERTEXT_BYTES = 16 * 1024
NOT_BASE64 = "ö" * 24


def to_base64(length):
    return base64.b64encode(bytes(length)).decode()


def sign_up_and_log_in(client, username):
    # The test client holds one session, so this logs out whoever was logged in before
    sign_up(client, username)
    response = log_in(client, username)

    assert response.status_code == 200


def test_send_requires_login(client):
    response = send(client, "bob")

    assert response.status_code == 401


def test_send_to_unknown_recipient(client):
    sign_up_and_log_in(client, "alice")

    response = send(client, "nobody")

    assert response.status_code == 404


def test_send_missing_fields(client):
    sign_up(client, "bob")
    sign_up_and_log_in(client, "alice")

    complete = {
        "recipient": "bob",
        "ciphertext": CIPHERTEXT,
        "key_for_recipient": KEY_FOR_RECIPIENT,
        "key_for_sender": KEY_FOR_SENDER,
        "signature": SIGNATURE,
    }
    for missing in complete:
        body = {field: value for field, value in complete.items() if field != missing}

        assert client.post("/api/messages", json=body).status_code == 400

    # The complete request is valid
    assert client.post("/api/messages", json=complete).status_code == 201


def test_send_malformed_fields(client):
    sign_up(client, "bob")
    sign_up_and_log_in(client, "alice")

    for field in ["ciphertext", "key_for_recipient", "key_for_sender", "signature"]:
        for bad_value in ["", "not base64!", NOT_BASE64]:
            response = send(client, "bob", **{field: bad_value})

            assert response.status_code == 400


def test_send_wrong_length_fields(client):
    sign_up(client, "bob")
    sign_up_and_log_in(client, "alice")

    for length in [91, 93]:
        assert send(client, "bob", key_for_recipient=to_base64(length)).status_code == 400
        assert send(client, "bob", key_for_sender=to_base64(length)).status_code == 400

    for length in [63, 65]:
        assert send(client, "bob", signature=to_base64(length)).status_code == 400


def test_send_ciphertext_size_limit(client):
    sign_up(client, "bob")
    sign_up_and_log_in(client, "alice")

    too_big = send(client, "bob", ciphertext=to_base64(MAX_CIPHERTEXT_BYTES + 1))
    largest_allowed = send(client, "bob", ciphertext=to_base64(MAX_CIPHERTEXT_BYTES))

    assert too_big.status_code == 400
    assert largest_allowed.status_code == 201


def test_plaintext_body_is_never_stored_or_returned(client):
    sign_up(client, "bob")
    sign_up_and_log_in(client, "alice")

    response = client.post(
        "/api/messages",
        json={
            "recipient": "bob",
            "body": "Hi Bob!",
            "ciphertext": CIPHERTEXT,
            "key_for_recipient": KEY_FOR_RECIPIENT,
            "key_for_sender": KEY_FOR_SENDER,
            "signature": SIGNATURE,
        },
    )

    assert response.status_code == 201
    assert "body" not in response.json
    assert b"Hi Bob!" not in client.get("/api/messages/outbox").data


def test_inbox_requires_login(client):
    assert client.get("/api/messages/inbox").status_code == 401
    assert client.get("/api/messages/outbox").status_code == 401


def test_message_lands_in_outbox_and_inbox(client):
    sign_up(client, "bob")
    sign_up_and_log_in(client, "alice")

    response = send(client, "bob")
    assert response.status_code == 201
    assert response.json["sender"] == "alice"
    assert response.json["recipient"] == "bob"
    assert response.json["read_at"] is None

    # Check there is the message in alice outbox
    outbox = client.get("/api/messages/outbox").json["messages"]
    assert [m["ciphertext"] for m in outbox] == [CIPHERTEXT]

    # Check there are not any messages in alice inbox
    assert client.get("/api/messages/inbox").json["messages"] == []

    sign_up_and_log_in(client, "bob")
    inbox = client.get("/api/messages/inbox").json["messages"]
    assert len(inbox) == 1
    assert inbox[0]["sender"] == "alice"
    assert inbox[0]["ciphertext"] == CIPHERTEXT
    assert inbox[0]["key_for_recipient"] == KEY_FOR_RECIPIENT
    assert inbox[0]["key_for_sender"] == KEY_FOR_SENDER
    assert inbox[0]["signature"] == SIGNATURE
    assert inbox[0]["sender_sign_public_key"] == SIGN_PUBLIC_KEY


def test_inbox_is_newest_first(client):
    first = base64.b64encode(b"first ciphertext").decode()
    second = base64.b64encode(b"second ciphertext").decode()
    sign_up(client, "bob")
    sign_up_and_log_in(client, "alice")
    send(client, "bob", ciphertext=first)
    send(client, "bob", ciphertext=second)

    sign_up_and_log_in(client, "bob")
    inbox = client.get("/api/messages/inbox").json["messages"]

    assert [msg["ciphertext"] for msg in inbox] == [second, first]
