from helpers import (
    CIPHERTEXT,
    KEY_FOR_RECIPIENT,
    KEY_FOR_SENDER,
    SIGNATURE,
    make_db_message,
    make_db_user,
)

from secure_messaging.extensions import db
from secure_messaging.models import Message, User


def test_user_round_trip(app):
    alice = make_db_user(username="alice")
    db.session.add(alice)
    db.session.commit()
    alice_id = alice.id

    db.session.expunge_all()

    loaded = db.session.get(User, alice_id)
    assert loaded is not None
    assert loaded.username == "alice"
    assert loaded.created_at is not None


def test_message_round_trip(app):
    alice = make_db_user(username="alice")
    bob = make_db_user(username="bob")
    db.session.add_all([alice, bob])
    db.session.commit()

    msg = make_db_message(sender_id=alice.id, recipient_id=bob.id)
    db.session.add(msg)
    db.session.commit()
    msg_id, alice_id, bob_id = msg.id, alice.id, bob.id

    db.session.expunge_all()

    loaded = db.session.get(Message, msg_id)
    assert loaded is not None
    assert loaded.sender_id == alice_id
    assert loaded.recipient_id == bob_id
    assert loaded.ciphertext == CIPHERTEXT
    assert loaded.key_for_recipient == KEY_FOR_RECIPIENT
    assert loaded.key_for_sender == KEY_FOR_SENDER
    assert loaded.signature == SIGNATURE
    assert loaded.created_at is not None
    assert loaded.read_at is None
