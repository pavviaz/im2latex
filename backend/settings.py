import os

from pydantic_settings import BaseSettings

RUN_LEVEL = os.getenv("RUN_LEVEL", "development")


class ToolConfig:
    env_file_encoding = "utf8"
    extra = "ignore"


class AppSettings(BaseSettings):
    PORT: int = 8080
    JWT_SECRET: str = "secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_H: int = 48
    COOKIE_NAME: str = "deepscriptum_cookie"

    class Config(ToolConfig):
        env_prefix = "app_"


class PostgresSettings(BaseSettings):
    HOST: str = "localhost"
    PORT: int = 5432
    USER: str = "postgres"
    PASSWORD: str = "passwd"
    DB: str = "ds"
    MAX_OVERFLOW: int = 15
    POOL_SIZE: int = 15

    URI: str = f"postgresql+asyncpg://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB}"
    ALEMBIC_URI: str = f"postgresql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB}"

    class Config(ToolConfig):
        env_prefix = "postgres_"


postgres_settings = PostgresSettings()
app_settings = AppSettings()
