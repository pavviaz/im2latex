from http import HTTPStatus
from typing import Optional


class BaseAPIException(Exception):
    def __init__(self, *, status_code: HTTPStatus, detail: str):
        self.detail = detail
        self.status_code = status_code


class EntityNotFoundError(BaseAPIException):
    def __str__(self):
        return self.detail

    def __init__(self, *, detail: Optional[str] = None):
        super().__init__(detail=detail or "no data", status_code=HTTPStatus.NOT_FOUND)


class EntityAlreadyExistsError(BaseAPIException):
    def __str__(self):
        return self.detail

    def __init__(self, *, detail: str):
        super().__init__(detail=detail, status_code=HTTPStatus.CONFLICT)


class BaseAuthError:
    def __init__(self, *, detail: str):
        super().__init__(detail=detail, status_code=HTTPStatus.FORBIDDEN)


class InvalidTokenError(BaseAuthError):
    pass


class InvalidCredentialsError(BaseAuthError):
    pass
