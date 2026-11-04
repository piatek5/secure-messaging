import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from secure_messaging.extensions import Base


class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    kdf_salt: Mapped[str] = mapped_column(String(24))  # 16 random bytes in base64
    enc_public_key: Mapped[str] = mapped_column(String(44))  # 32 bytes in base64
    sign_public_key: Mapped[str] = mapped_column(String(44))  # 32 bytes in base64
    wrapped_enc_private_key: Mapped[str] = mapped_column(Text)
    wrapped_sign_private_key: Mapped[str] = mapped_column(Text)
    username: Mapped[str] = mapped_column(String(32), unique=True)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())


class Message(Base):
    __tablename__ = "message"
    id: Mapped[int] = mapped_column(primary_key=True)
    ciphertext: Mapped[str] = mapped_column(Text)
    key_for_recipient: Mapped[str] = mapped_column(String(124))  # 92 bytes in base64
    key_for_sender: Mapped[str] = mapped_column(String(124))  # 92 bytes in base64
    signature: Mapped[str] = mapped_column(String(88))  # 64 bytes in base64
    sender_id: Mapped[int] = mapped_column(ForeignKey(User.id), index=True)
    sender: Mapped[User] = relationship(foreign_keys=[sender_id])
    recipient_id: Mapped[int] = mapped_column(ForeignKey(User.id), index=True)
    recipient: Mapped[User] = relationship(foreign_keys=[recipient_id])
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
    read_at: Mapped[datetime.datetime | None]
