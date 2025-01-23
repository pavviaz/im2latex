from fastapi import APIRouter, Depends, Response
from fastapi.security import OAuth2PasswordRequestForm

from api.dependencies import get_auth_repository
from backend.infrastructure.postgres.service.auth.repo import UserAuthRepository
from domain.auth.model import Token, Token, UserAuth
from settings import app_settings


router = APIRouter(prefix="/auth", tags=["Authorization"])


@router.post("/login", response_model=Token)
async def login(
    auth_form: OAuth2PasswordRequestForm = Depends(),
    user_auth_service: UserAuthRepository = Depends(get_auth_repository),
):
    return await user_auth_service.authenticate_user(auth_form)


@router.post("/logout")
async def logout(
    response: Response,
):
    response.delete_cookie(key=app_settings.COOKIE_NAME)
    return response


@router.post("/register", response_model=Token)
async def register(
    user_data: UserAuth,
    user_auth_service: UserAuthRepository = Depends(get_auth_repository),
):
    token = await user_auth_service.register_new_user(user_data)
    return Token(data=token)
