import re

from flask import Blueprint, request, session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from secure_messaging.extensions import db
from secure_messaging.models import User, Message

bp = Blueprint("api", __name__, url_prefix="/api")

USERNAME_RE = re.compile(r"[a-zA-Z0-9_]{3,32}")


@bp.get("/health")
def health():
    return {"status": "ok"}


@bp.post("/users")
def create_user():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    if not isinstance(username, str) or not USERNAME_RE.fullmatch(username):
        return {"error": "username must be 3-32 letters, digits or _"}, 400

    user = User(username=username)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return {"error": "username taken"}, 409

    return {"id": user.id, "username": user.username}, 201


def current_user() -> User | None:
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id is not None else None


# Insecure stand-in logs in by username alone
@bp.post("/session")
def log_in():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    if not isinstance(username, str):
        return {"error": "username required"}, 400

    user = db.session.execute(db.select(User).where(User.username == username)).scalar_one_or_none()
    if user is None:
        return {"error": "unknown user"}, 404

    session.clear()
    session["user_id"] = user.id
    return {"id": user.id, "username": user.username}


@bp.get("/session")
def who_am_i():
    user = current_user()
    if user is None:
        return {"error": "not logged in"}, 401
    return {"id": user.id, "username": user.username}


@bp.delete("/session")
def log_out():
    session.clear()
    return "", 204


def message_to_dict(message: Message) -> dict:
    return {
        "id": message.id,
        "sender": message.sender.username,
        "recipient": message.recipient.username,
        "body": message.body,
        "created_at": message.created_at.isoformat(),
        "read_at": message.read_at.isoformat() if message.read_at else None,
    }


@bp.post("/messages")
def send_message():
    user = current_user()
    if user is None:
        return {"error": "not logged in"}, 401

    data = request.get_json(silent=True) or {}
    recipient_name = data.get("recipient")
    body = data.get("body")
    if not isinstance(recipient_name, str) or not isinstance(body, str):
        return {"error": "recipient and body required"}, 400
    if not 1 <= len(body) <= 2000:
        return {"error": "body must be 1-2000 characters"}, 400

    recipient = db.session.execute(
        db.select(User).where(User.username == recipient_name)
    ).scalar_one_or_none()
    if recipient is None:
        return {"error": "unknown recipient"}, 404

    message = Message(sender_id=user.id, recipient_id=recipient.id, body=body)
    db.session.add(message)
    db.session.commit()
    return message_to_dict(message), 201


@bp.get("/messages/inbox")
def inbox():
    user = current_user()
    if user is None:
        return {"error": "not logged in"}, 401

    messages = db.session.execute(
        db.select(Message)
        .where(Message.recipient_id == user.id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .options(selectinload(Message.sender), selectinload(Message.recipient))
    ).scalars().all()
    return {"messages": [message_to_dict(m) for m in messages]}


@bp.get("/messages/outbox")
def outbox():
    user = current_user()
    if user is None:
        return {"error": "not logged in"}, 401

    messages = db.session.execute(
        db.select(Message)
        .where(Message.sender_id == user.id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .options(selectinload(Message.sender), selectinload(Message.recipient))
    ).scalars().all()
    return {"messages": [message_to_dict(m) for m in messages]}
