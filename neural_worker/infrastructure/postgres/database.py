from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from settings import postgres_settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    postgres_settings.URI,  # Изменено
)
session_factory = sessionmaker(
    bind=engine,  # Изменено
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

from .models import *  # pylint: disable=C0413  # isort:skip  # noqa: F403, E402
