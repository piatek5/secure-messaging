import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from secure_messaging.extensions import Base


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())


class Message(Base):
    __tablename__ = "message"
    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey(User.id), index=True)
    sender: Mapped[User] = relationship(foreign_keys=[sender_id])
    recipient_id: Mapped[int] = mapped_column(ForeignKey(User.id), index=True)
    recipient: Mapped[User] = relationship(foreign_keys=[recipient_id])
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
    read_at: Mapped[datetime.datetime | None]
