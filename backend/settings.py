import os

from pydantic import BaseSettings

RUN_LEVEL = os.getenv("RUN_LEVEL", "development")


class ToolConfig:
    env_file_encoding = "utf8"
    extra = "ignore"


class AppSettings(BaseSettings):
    PORT: int = 8080
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_H: int = 48
    COOKIE_NAME: str = "deepscriptum_cookie"

    class Config(ToolConfig):
        env_prefix = "app_"


class PostgresSettings(BaseSettings):
    HOST: str = "postgres"
    PORT: int = 5432
    USER: str = "ds"
    PASSWORD: str = "passwd"
    DB: str = "ds"
    MAX_OVERFLOW: int = 15
    POOL_SIZE: int = 15

    URI = f"postgresql+asyncpg://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB}"
    ALEMBIC_URI = f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB}"

    class Config(ToolConfig):
        env_prefix = "postgres_"


postgres_settings = PostgresSettings()
app_settings = AppSettings()
