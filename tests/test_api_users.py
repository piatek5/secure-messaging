from helpers import sign_up


def test_sign_up_proper_user(client):
    response = sign_up(client, "alice")

    assert response.json["username"] == "alice"
    assert response.status_code == 201


def test_sign_up_wrong_username(client):
    response = sign_up(client, "a!ice")

    assert response.status_code == 400


def test_sign_up_no_username(client):
    response = client.post("/api/users", json={"not_username": "alice"})

    assert response.status_code == 400


def test_sign_up_doubled_username(client):
    response = sign_up(client, "alice")
    response = sign_up(client, "alice")

    assert response.status_code == 409
