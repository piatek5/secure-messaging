def test_health_request(client):
    response = client.get("/api/health")
    assert response.is_json
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
