from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from settings import postgres_settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    postgres_settings.URI,
)
async_session_factory = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


from .models import *  # pylint: disable=C0413  # isort:skip  # noqa: F403, E402
