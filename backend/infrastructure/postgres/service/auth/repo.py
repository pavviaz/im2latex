from typing import Optional
from datetime import datetime, timedelta

import bcrypt
from fastapi.security import OAuth2PasswordRequestForm
import sqlalchemy as sa
from jose import jwt, JWTError
from pydantic import ValidationError

from domain.auth.model import BaseUser, JWTPayload, Token, UserAuth
from domain.exceptions import InvalidCredentialsError, InvalidTokenError
from infrastructure.postgres.models import UserDAO
from settings import app_settings


class UserAuthRepository:
    def __init__(self, session):
        self.session = session

    @classmethod
    def hash_password(cls, password: str) -> str:
        return bcrypt.hash(password)

    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.verify(plain_password, hashed_password)

    @classmethod
    def verify_token(cls, token: str) -> BaseUser:
        try:
            payload_raw = jwt.decode(
                token, app_settings.JWT_SECRET, algorithms=[app_settings.JWT_ALGORITHM]
            )
            payload = JWTPayload.model_validate(payload_raw)
        except (JWTError, ValidationError):
            raise InvalidTokenError(detail="Could not validate credentials")

        return payload.user

    @classmethod
    def create_token(cls, user: UserDAO) -> Token:
        now = datetime.utcnow()
        jwt_payload = JWTPayload(
            user=BaseUser(email=user.email),
            sub=str(user.id),
            iat=now,
            exp=now + timedelta(hours=app_settings.JWT_EXPIRES_H),
        )
        token = jwt.encode(
            jwt_payload.model_dump(),
            app_settings.JWT_SECRET,
            algorithm=app_settings.JWT_ALGORITHM,
        )
        return Token(access_token=token)

    async def register_new_user(self, user_data: UserAuth) -> Token:
        user = await self.get_by_email(user_data.email)

        if user:
            raise InvalidCredentialsError(detail="User with such email already exists")

        new_user = await self.create_user(user_data)

        return self.create_token(new_user)

    async def authenticate_user(self, auth_form: UserAuth) -> Token:
        user = await self.get_by_email(auth_form.email)

        if not user:
            raise InvalidCredentialsError(detail="No such user")

        if not self.verify_password(auth_form.password, user.password_hash):  # type: ignore
            raise InvalidCredentialsError(detail="Incorrect password")

        token = self.create_token(user)

        return token

    async def create_user(self, user_data: UserAuth) -> UserDAO:
        new_user = UserDAO(
            email=user_data.email,
            password_hash=self.hash_password(user_data.password),
        )
        self.session.add(new_user)
        await self.session.commit()
        return new_user

    async def get_by_email(self, email: str) -> Optional[UserDAO]:
        stmt = sa.select(UserDAO).filter_by(email=email)
        return (await self.session.execute(stmt)).scalar()
