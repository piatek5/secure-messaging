import pytest
from sqlalchemy.exc import IntegrityError

from secure_messaging.extensions import db
from secure_messaging.models import Message


def test_message_with_unknown_users(app):
    # The user table is empty, so neither id exists
    msg = Message(sender_id=1, recipient_id=2, body="Hi nobody!")
    db.session.add(msg)

    with pytest.raises(IntegrityError):
        db.session.commit()
