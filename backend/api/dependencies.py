from typing import Type

from fastapi import Depends, Request
from infrastructure.postgres.service.auth.repo import UserAuthRepository
from domain.auth.model import BaseUser
from settings import app_settings
from sqlalchemy.ext.asyncio import AsyncSession


def get_db(request: Request):
    return request.state.db


def get_auth_repository(
    session: AsyncSession = Depends(get_db),
):
    return UserAuthRepository(session)


def get_current_user(request: Request) -> str:
    token = request.cookies.get(app_settings.COOKIE_NAME, "")
    return UserAuthRepository.verify_token(token)
