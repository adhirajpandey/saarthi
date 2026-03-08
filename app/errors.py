"""Application-specific error types."""


class AppError(Exception):
    """Domain-level API error translated by the global exception handler."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)
