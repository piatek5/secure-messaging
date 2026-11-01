import pytest

from secure_messaging import create_app


def test_no_key_error(monkeypatch, tmp_path):
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    monkeypatch.setenv("SECURE_MESSAGING_INSTANCE_PATH", str(tmp_path))

    with pytest.raises(RuntimeError):
        create_app()
