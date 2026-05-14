"""Custom HTTP exception classes — auth-specific and generic."""

from fastapi import HTTPException, status


class CredentialsException(HTTPException):
    def __init__(self, detail: str = "Invalid credentials") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class TokenExpiredException(HTTPException):
    def __init__(self, detail: str = "Token has expired") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class EmailAlreadyExistsException(HTTPException):
    def __init__(self, detail: str = "Email already registered") -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class UserNotFoundException(HTTPException):
    def __init__(self, detail: str = "User not found") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class InactiveUserException(HTTPException):
    def __init__(self, detail: str = "Inactive user account") -> None:
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class NotFound(HTTPException):
    def __init__(self, detail: str = "Resource not found") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class BadRequest(HTTPException):
    def __init__(self, detail: str = "Bad request") -> None:
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
