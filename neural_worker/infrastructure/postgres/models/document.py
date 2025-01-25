import uuid
import enum
from datetime import datetime

from sqlalchemy import String, TIMESTAMP, Enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from infrastructure.postgres.database import Base


class ShareRoleEnum(enum.Enum):
    private = "закрытый доступ"
    viewer = "только просмотр"
    edit = "редактирование"


class DocumentDAO(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100))
    s3_md_id: Mapped[str] = mapped_column(String(50), nullable=True)
    s3_raw_id: Mapped[str] = mapped_column(String(50), nullable=True)
    upload_date: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    common_share_role_type: Mapped[ShareRoleEnum] = mapped_column(
        type_=Enum(ShareRoleEnum), default=ShareRoleEnum.private
    )
