import pytest
from sqlalchemy.exc import IntegrityError

from secure_messaging.extensions import db
from secure_messaging.models import User


def test_duplicate_username(app):
    alice = User(username="alice")
    the_other_alice = User(username="alice")
    db.session.add(alice)
    db.session.add(the_other_alice)

    with pytest.raises(IntegrityError):
        db.session.commit()
