def sign_up_and_log_in(client, username):
    # The test client holds one session, so this logs out whoever was logged in before
    client.post("/api/users", json={"username": username})
    response = client.post("/api/session", json={"username": username})
    assert response.status_code == 200


def send(client, recipient, body):
    return client.post("/api/messages", json={"recipient": recipient, "body": body})


def test_send_requires_login(client):
    response = send(client, "bob", "Hi Bob!")

    assert response.status_code == 401


def test_send_to_unknown_recipient(client):
    sign_up_and_log_in(client, "alice")

    response = send(client, "nobody", "Hi?")

    assert response.status_code == 404


def test_send_empty_body(client):
    client.post("/api/users", json={"username": "bob"})
    sign_up_and_log_in(client, "alice")

    response = send(client, "bob", "")

    assert response.status_code == 400


def test_send_missing_fields(client):
    sign_up_and_log_in(client, "alice")

    response = client.post("/api/messages", json={"recipient": "bob"})

    assert response.status_code == 400


def test_inbox_requires_login(client):
    assert client.get("/api/messages/inbox").status_code == 401
    assert client.get("/api/messages/outbox").status_code == 401


def test_message_lands_in_outbox_and_inbox(client):
    client.post("/api/users", json={"username": "bob"})
    sign_up_and_log_in(client, "alice")

    response = send(client, "bob", "Hi Bob!")
    assert response.status_code == 201
    assert response.json["sender"] == "alice"
    assert response.json["recipient"] == "bob"
    assert response.json["read_at"] is None

    # Check there is the messeage in alice outbox
    outbox = client.get("/api/messages/outbox").json["messages"]
    assert [m["body"] for m in outbox] == ["Hi Bob!"]

    # Check there are not any messeages in alice inbox
    assert client.get("/api/messages/inbox").json["messages"] == []

    sign_up_and_log_in(client, "bob")
    inbox = client.get("/api/messages/inbox").json["messages"]
    assert len(inbox) == 1
    assert inbox[0]["sender"] == "alice"
    assert inbox[0]["body"] == "Hi Bob!"


def test_inbox_is_newest_first(client):
    client.post("/api/users", json={"username": "bob"})
    sign_up_and_log_in(client, "alice")
    send(client, "bob", "first")
    send(client, "bob", "second")

    sign_up_and_log_in(client, "bob")
    inbox = client.get("/api/messages/inbox").json["messages"]

    assert [m["body"] for m in inbox] == ["second", "first"]
