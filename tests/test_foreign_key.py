import pytest
from helpers import make_db_message
from sqlalchemy.exc import IntegrityError

from secure_messaging.extensions import db


def test_message_with_unknown_users(app):
    # The user table is empty, so neither id exists
    msg = make_db_message(sender_id=1, recipient_id=2)
    db.session.add(msg)

    with pytest.raises(IntegrityError):
        db.session.commit()
