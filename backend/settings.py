from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field


class ToolConfig:
    env_file_encoding = "utf8"
    extra = "ignore"


class AppSettings(BaseSettings):
    PORT: int = 8080
    JWT_SECRET: str = "secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_H: int = 48
    COOKIE_NAME: str = "deepscriptum_cookie"

    HC_TIMEOUT: int = 30  # secs
    HC_SLEEP: int = 5  # secs

    class Config(ToolConfig):
        env_prefix = "api_"


class RedisSettings(BaseSettings):
    HOST: str = "redis"
    PORT: int = 6379
    DB: int = 0

    URI: str = f"redis://{HOST}:{PORT}/{DB}"

    class Config(ToolConfig):
        env_prefix = "redis_"


class RabbitMQSettings(BaseSettings):
    HOST: str = "rabbitmq"
    AMQP_PORT: int = 5672
    LOGIN: str = "admin"
    PASSWORD: str = "admin"

    URI: str = f"amqp://{LOGIN}:{PASSWORD}@{HOST}:{AMQP_PORT}/"

    class Config(ToolConfig):
        env_prefix = "rabbitmq_"


class MinIOSettings(BaseSettings):
    HOST: str = "minio"
    BUCKET: str = "user_docs"
    API_PORT: int = 9000
    ROOT_USER: str = "admin"
    ROOT_PASSWORD: str = "admin_password"

    URI: str = f"http://{HOST}:{API_PORT}"

    class Config(ToolConfig):
        env_prefix = "minio_"


class PostgresSettings(BaseSettings):
    HOST: str = "localhost"
    PORT: int = 5432
    USER: str = "postgres"
    PASSWORD: str = "passwd"
    DB: str = "ds"
    MAX_OVERFLOW: int = 15
    POOL_SIZE: int = 15

    @computed_field(return_type=str)
    @property
    def URI(self):
        return f"postgresql+asyncpg://{self.USER}:{self.PASSWORD}@{self.HOST}:{self.PORT}"
    
    class Config(ToolConfig):
        env_prefix = "postgres_"


postgres_settings = PostgresSettings()
app_settings = AppSettings()
redis_settings = RedisSettings()
minio_settings = MinIOSettings()
rabbitmq_settings = RabbitMQSettings()
