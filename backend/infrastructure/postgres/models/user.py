import enum
import uuid
from datetime import datetime

from sqlalchemy import String, ForeignKey, TIMESTAMP, Enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from domain.auth.model import RoleEnum
from infrastructure.postgres.database import Base


# TODO: Remove with Enum?
class SubscriptionDAO(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(20))
    #price ...? 


class UserDAO(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column()
    name: Mapped[str] = mapped_column(String(100), nullable=True)
    # register_date: Mapped[date]
    sub_level_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id"))


class DocumentUserDAO(Base):
    __tablename__ = "document_users"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id"), primary_key=True
    )
    last_access_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.now()
    )
    role: Mapped[RoleEnum] = mapped_column(type_=Enum(RoleEnum))
