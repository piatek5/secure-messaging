import re

from flask import Blueprint, request
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
