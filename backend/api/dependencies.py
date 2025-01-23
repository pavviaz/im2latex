from typing import Type

from fastapi import Depends, Request
from infrastructure.postgres.service.auth.repo import UserAuthRepository
from sqlalchemy.ext.asyncio import AsyncSession


def get_db(request: Request):
    return request.state.db


def get_auth_repository(
    session: AsyncSession = Depends(get_db),
):
    return UserAuthRepository(session)
