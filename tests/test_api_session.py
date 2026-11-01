def test_log_in_unknown(client):
    response = client.post("/api/session", json={"username": "no_bob_here"})

    assert response.status_code == 404


def test_log_in_known(client):
    client.post("/api/users", json={"username": "alice"})

    response = client.post("/api/session", json={"username": "alice"})

    assert response.status_code == 200

    response = client.get("/api/session")

    assert response.json["username"] == "alice"


def test_get_current_user_not_logged(client):
    response = client.get("/api/session")

    assert response.status_code == 401


def test_log_in_log_out_get_current_user(client):
    client.post("/users", json={"username": "alice"})

    # Log in
    client.post("/api/session", json={"username": "alice"})

    # Log out
    response = client.delete("/api/session")

    assert response.status_code == 204

    # Who am i
    response = client.get("/api/session")

    assert response.status_code == 401
