from helpers import log_in, sign_up


def test_log_in_unknown(client):
    response = log_in(client, "no_bob_here")

    assert response.status_code == 401


def test_log_in_known(client):
    response = sign_up(client, "alice")

    response = log_in(client, "alice")

    assert response.status_code == 200

    response = client.get("/api/session")

    assert response.json["username"] == "alice"


def test_get_current_user_not_logged(client):
    response = client.get("/api/session")

    assert response.status_code == 401


def test_sign_in_log_in_log_out_get_current_user(client):
    sign_up(client, "alice")

    log_in(client, "alice")

    # Log out
    response = client.delete("/api/session")

    assert response.status_code == 204

    # Who am i
    response = client.get("/api/session")

    assert response.status_code == 401
