"""
Custom exception hierarchy for Chispart AI - Blackbox Hybrid Tool.
Provides unified error handling throughout the application.
"""

from fastapi import HTTPException, status


class ChispartException(Exception):
    """Base class for all Chispart AI exceptions."""
    pass


class ChispartAPIException(HTTPException):
    """
    Common HTTP exception for Chispart AI API.
    Provides a consistent response format.
    """
    def __init__(self, status_code: int, detail: str, headers: dict = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class InvalidTokenException(ChispartAPIException):
    """Raised when a provided token is invalid or missing."""
    def __init__(self, detail: str = "Invalid or missing token"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


class RateLimitExceededException(ChispartAPIException):
    """Raised when a request exceeds configured rate limits."""
    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail
        )
