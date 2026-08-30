"""HTTP klijent za desktop → backend API (DENT-IMPROVE-020).

Isključivo za ``desktop/remote_demo.py`` — glavna desktop aplikacija
(``desktop/app.py``/``main_window.py``) ostaje na lokalnoj SQLite bazi,
nepromijenjena.
"""

from desktop.api_client.client import (
    ApiClientError,
    AuthenticationFailedError,
    ConnectionFailedError,
    DentalandApiClient,
    PermissionDeniedError,
    RateLimitedError,
    ServerError,
)

__all__ = [
    "ApiClientError",
    "AuthenticationFailedError",
    "ConnectionFailedError",
    "DentalandApiClient",
    "PermissionDeniedError",
    "RateLimitedError",
    "ServerError",
]
