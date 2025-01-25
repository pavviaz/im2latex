from pydantic_settings import BaseSettings
from pydantic import computed_field


class ToolConfig:
    env_file_encoding = "utf8"
    extra = "ignore"


class BackendAppSettings(BaseSettings):
    HOST: str = "backend"
    PORT: int = 8080
    JWT_SECRET: str = "secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_H: int = 48
    COOKIE_NAME: str = "ds_auth"

    HC_TIMEOUT: int = 30  # secs
    HC_SLEEP: int = 5  # secs

    @computed_field(return_type=str)
    @property
    def URI(self):
        return f"http://{self.HOST}:{self.PORT}/"

    class Config(ToolConfig):
        env_prefix = "api_"


class FrontAppSettings(BaseSettings):
    PORT: int = 5000

    class Config(ToolConfig):
        env_prefix = "front_"


back_settings = BackendAppSettings()
front_settings = FrontAppSettings()
