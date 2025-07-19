class CustomException(Exception):
    """Base class for custom exceptions in this project."""

class SignatureError(CustomException):
    """Exception raised for signature validation errors."""
    pass