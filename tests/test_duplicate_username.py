import pytest
from helpers import make_db_user
from sqlalchemy.exc import IntegrityError

from secure_messaging.extensions import db


def test_duplicate_username(app):
    alice = make_db_user(username="alice")
    db.session.add(alice)
    db.session.commit()

    the_other_alice = make_db_user(username="alice")
    db.session.add(the_other_alice)

    with pytest.raises(IntegrityError):
        db.session.commit()
