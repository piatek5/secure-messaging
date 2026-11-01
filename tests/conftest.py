import pytest

from secure_messaging import create_app


@pytest.fixture()
def app(monkeypatch, tmp_path):
    monkeypatch.setenv("SECURE_MESSAGING_INSTANCE_PATH", str(tmp_path))

    app = create_app(
        test_config={
            "TESTING": True,
            "SECRET_KEY": "dummy",
        }
    )

    yield app


@pytest.fixture()
def client(app):
    return app.test_client()
