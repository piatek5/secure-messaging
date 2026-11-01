def test_proper_user(client):
    response = client.post("/api/users", json={"username": "alice"})

    assert response.json["username"] == "alice"
    assert response.status_code == 201


def test_wrong_username(client):
    response = client.post("/api/users", json={"username": "a!ice"})

    assert response.status_code == 400


def test_no_username(client):
    response = client.post("/api/users", json={"not_username": "alice"})

    assert response.status_code == 400


def test_doubled_username(client):
    response = client.post("/api/users", json={"username": "alice"})
    response = client.post("/api/users", json={"username": "alice"})

    assert response.status_code == 409
