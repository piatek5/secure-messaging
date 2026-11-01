import re

from flask import Blueprint, request, session
from sqlalchemy.exc import IntegrityError

from secure_messaging.extensions import db
from secure_messaging.models import User

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
