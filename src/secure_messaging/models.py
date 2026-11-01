import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from secure_messaging.extensions import db


class User(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    # Filled in by the database itself (UTC), also for rows inserted outside the ORM
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())


class Message(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey(User.id), index=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey(User.id), index=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
    # None until the recipient reads the message
    read_at: Mapped[datetime.datetime | None]
