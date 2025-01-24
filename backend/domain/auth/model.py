import enum
from datetime import datetime

from pydantic import BaseModel, Field


class RoleEnum(enum.Enum):
    owner = "создать"
    viewer = "зритель"
    editor = "редактор"


class BaseUser(BaseModel):
    email: str

    class Config:
        from_attributes = True


class UserAuth(BaseUser):
    password: str = Field(min_length=4)


class JWTPayload(BaseModel):
    user: BaseUser
    sub: str
    iat: datetime
    exp: datetime


class Token(BaseModel):
    access_token: str
