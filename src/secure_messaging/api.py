import base64
import hashlib
import hmac
import re
from functools import cache

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from flask import Blueprint, current_app, request, session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from secure_messaging.extensions import db
from secure_messaging.models import Message, User

bp = Blueprint("api", __name__, url_prefix="/api")

ph = PasswordHasher()

USERNAME_RE = re.compile(r"[a-zA-Z0-9_]{3,32}")
MAX_CIPHERTEXT_BYTES = 16 * 1024


@cache
def dummy_hash() -> str:
    return ph.hash("dummy")


def is_base64_of_length(value: str, length: int) -> bool:
    try:
        return len(base64.b64decode(value, validate=True)) == length
    except ValueError:
        return False


def is_base64_up_to(value: str, max_length: int) -> bool:
    try:
        return 0 < len(base64.b64decode(value, validate=True)) <= max_length
    except ValueError:
        return False


def own_keys(user: User) -> dict:
    return {
        "enc_public_key": user.enc_public_key,
        "sign_public_key": user.sign_public_key,
        "wrapped_enc_private_key": user.wrapped_enc_private_key,
        "wrapped_sign_private_key": user.wrapped_sign_private_key,
    }


@bp.get("/health")
def health():
    return {"status": "ok"}


@bp.post("/users")
def create_user():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    if not isinstance(username, str) or not USERNAME_RE.fullmatch(username):
        return {"error": "username must be 3-32 letters, digits or _"}, 400

    kdf_salt = data.get("kdf_salt")
    auth_token = data.get("auth_token")
    enc_public_key = data.get("enc_public_key")
    sign_public_key = data.get("sign_public_key")
    wrapped_enc_private_key = data.get("wrapped_enc_private_key")
    wrapped_sign_private_key = data.get("wrapped_sign_private_key")
    if (
        not isinstance(kdf_salt, str)
        or not isinstance(auth_token, str)
        or not isinstance(enc_public_key, str)
        or not isinstance(sign_public_key, str)
        or not isinstance(wrapped_enc_private_key, str)
        or not isinstance(wrapped_sign_private_key, str)
        or not is_base64_of_length(kdf_salt, 16)
        or not is_base64_of_length(auth_token, 32)
        or not is_base64_of_length(enc_public_key, 32)
        or not is_base64_of_length(sign_public_key, 32)
        or not is_base64_up_to(wrapped_enc_private_key, 256)
        or not is_base64_up_to(wrapped_sign_private_key, 256)
    ):
        return {"error": "invalid credentials format"}, 400

    user = User(
        username=username,
        password_hash=ph.hash(auth_token),
        kdf_salt=kdf_salt,
        enc_public_key=enc_public_key,
        sign_public_key=sign_public_key,
        wrapped_enc_private_key=wrapped_enc_private_key,
        wrapped_sign_private_key=wrapped_sign_private_key,
    )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return {"error": "username taken"}, 409

    return {"id": user.id, "username": user.username}, 201


@bp.get("/users/<username>/salt")
def get_salt(username: str):
    user = db.session.execute(db.select(User).where(User.username == username)).scalar_one_or_none()
    if user is not None:
        return {"kdf_salt": user.kdf_salt}
    # Generate a stable fake salt
    key = current_app.config["SECRET_KEY"].encode()
    fake = hmac.new(key, username.encode(), hashlib.sha256).digest()[:16]
    return {"kdf_salt": base64.b64encode(fake).decode()}


@bp.get("/users/<username>/keys")
def get_public_keys(username: str):
    if current_user() is None:
        return {"error": "not logged in"}, 401
    user = db.session.execute(db.select(User).where(User.username == username)).scalar_one_or_none()
    if user is None:
        return {"error": "unknown user"}, 404
    return {"enc_public_key": user.enc_public_key, "sign_public_key": user.sign_public_key}


def current_user() -> User | None:
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id is not None else None


@bp.post("/session")
def log_in():
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    auth_token = data.get("auth_token")
    if (
        not isinstance(username, str)
        or not isinstance(auth_token, str)
        or not is_base64_of_length(auth_token, 32)
    ):
        return {"error": "invalid credentials format"}, 400

    user = db.session.execute(db.select(User).where(User.username == username)).scalar_one_or_none()
    # Run Argon2 no matter if the user exists
    try:
        ph.verify(user.password_hash if user else dummy_hash(), auth_token)
    except VerifyMismatchError:
        return {"error": "wrong username or password"}, 401
    if user is None:
        return {"error": "wrong username or password"}, 401

    session.clear()
    session["user_id"] = user.id
    return {"id": user.id, "username": user.username, **own_keys(user)}


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
        "ciphertext": message.ciphertext,
        "key_for_recipient": message.key_for_recipient,
        "key_for_sender": message.key_for_sender,
        "signature": message.signature,
        "sender_sign_public_key": message.sender.sign_public_key,
        "created_at": message.created_at.isoformat(),
        "read_at": message.read_at.isoformat() if message.read_at else None,
    }


@bp.post("/messages")
def send_message():
    user = current_user()
    if user is None:
        return {"error": "not logged in"}, 401

    data = request.get_json(silent=True) or {}

    fields = ("ciphertext", "key_for_recipient", "key_for_sender", "signature", "recipient")
    if not all(isinstance(data.get(field), str) for field in fields):
        return {"error": "recipient and encrypted fields required"}, 400
    if (
        not is_base64_up_to(data["ciphertext"], MAX_CIPHERTEXT_BYTES)
        or not is_base64_of_length(data["key_for_recipient"], 92)
        or not is_base64_of_length(data["key_for_sender"], 92)
        or not is_base64_of_length(data["signature"], 64)
    ):
        return {"error": "invalid encrypted message format"}, 400

    recipient_name = data.get("recipient")
    ciphertext = data.get("ciphertext")
    key_for_recipient = data.get("key_for_recipient")
    key_for_sender = data.get("key_for_sender")
    signature = data.get("signature")

    recipient = db.session.execute(
        db.select(User).where(User.username == recipient_name)
    ).scalar_one_or_none()
    if recipient is None:
        return {"error": "unknown recipient"}, 404

    message = Message(
        sender_id=user.id,
        recipient_id=recipient.id,
        ciphertext=ciphertext,
        key_for_recipient=key_for_recipient,
        key_for_sender=key_for_sender,
        signature=signature,
    )

    db.session.add(message)
    db.session.commit()
    return message_to_dict(message), 201


@bp.get("/messages/inbox")
def inbox():
    user = current_user()
    if user is None:
        return {"error": "not logged in"}, 401

    messages = (
        db.session.execute(
            db.select(Message)
            .where(Message.recipient_id == user.id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .options(selectinload(Message.sender), selectinload(Message.recipient))
        )
        .scalars()
        .all()
    )
    return {"messages": [message_to_dict(m) for m in messages]}


@bp.get("/messages/outbox")
def outbox():
    user = current_user()
    if user is None:
        return {"error": "not logged in"}, 401

    messages = (
        db.session.execute(
            db.select(Message)
            .where(Message.sender_id == user.id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .options(selectinload(Message.sender), selectinload(Message.recipient))
        )
        .scalars()
        .all()
    )
    return {"messages": [message_to_dict(m) for m in messages]}
