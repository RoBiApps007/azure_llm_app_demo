from typing import Any, Optional

class BaseAppException(Exception):
    """
    Base exception for the entire project.
    Used to catch domain-specific errors.
    """
    def __init__(
        self, 
        message: str, 
        payload: Optional[dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.payload = payload

# --- Client Errors (4xx range) ---

class ClientError(BaseAppException):
    """Errors caused by incorrect user input.
    """
    pass

class ValidationError(ClientError):
    """Raised when data does not conform to the expected format."""
    pass

class UnauthorizedError(ClientError):
    """Errors related to authentication or missing permissions."""
    pass

# --- Concerto Spezifische Fehler ---

class ConcertoError(BaseAppException):
    """Base error for all issues within the concerto package."""
    pass

class SignalNotFoundError(ConcertoError, ClientError):
    """Raised when a requested signal is missing in the measurement."""
    pass

class MeasurementReadError(ConcertoError):
    """Raised when there is an error reading the physical measurement file (e.g., corruption)."""
    pass

# --- Server Errors (500 range) ---

class InternalServerError(BaseAppException):
    """Errors indicating a problem within our infrastructure."""
    pass