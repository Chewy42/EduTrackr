import logging
import os
import time
from typing import Any, Dict, Optional

import requests
from requests.exceptions import ConnectionError, HTTPError, RequestException, Timeout

logger = logging.getLogger(__name__)


class SupabaseError(Exception):
    """Base exception for Supabase-related errors."""

    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error


class SupabaseConnectionError(SupabaseError, ConnectionError):
    """Raised when unable to connect to Supabase.
    Inherits from ConnectionError for backward compatibility with existing catch blocks."""
    pass


class SupabaseTimeoutError(SupabaseError, Timeout):
    """Raised when a request to Supabase times out.
    Inherits from requests.exceptions.Timeout for backward compatibility."""
    pass


class SupabaseServerError(SupabaseError):
    """Raised when Supabase returns a 5xx error."""

    def __init__(self, message: str, status_code: int, original_error: Optional[Exception] = None):
        super().__init__(message, original_error)
        self.status_code = status_code


class SupabaseClientError(SupabaseError):
    """Raised when Supabase returns a 4xx error."""

    def __init__(self, message: str, status_code: int, response_body: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class SupabaseConfigError(SupabaseError, RuntimeError):
    """Raised when Supabase configuration is missing or invalid.
    Inherits from RuntimeError for backward compatibility with existing catch blocks."""
    pass


def _get_env(key: str, default: str = "") -> str:
    """Get environment variable, stripping whitespace."""
    return (os.getenv(key) or default).strip()


SUPABASE_URL = _get_env("SUPABASE_URL").rstrip("/")
SUPABASE_ANON_KEY = _get_env("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = _get_env("SUPABASE_SERVICE_ROLE_KEY") or _get_env("SUPABASE_ACCESS_TOKEN")

DEFAULT_TIMEOUT = int(_get_env("SUPABASE_TIMEOUT", "60"))
MAX_RETRIES = int(_get_env("SUPABASE_MAX_RETRIES", "3"))
INITIAL_BACKOFF = float(_get_env("SUPABASE_INITIAL_BACKOFF", "1.0"))


def supabase_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_ANON_KEY and SUPABASE_SERVICE_KEY)


def ensure_supabase_env() -> None:
    if not supabase_configured():
        missing = []
        if not SUPABASE_URL:
            missing.append("SUPABASE_URL")
        if not SUPABASE_ANON_KEY:
            missing.append("SUPABASE_ANON_KEY")
        if not SUPABASE_SERVICE_KEY:
            missing.append("SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ACCESS_TOKEN")
        raise SupabaseConfigError(f"Missing Supabase configuration: {', '.join(missing)}")


def supabase_headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_ANON_KEY or "",
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }


def _is_retryable_error(error: Exception) -> bool:
    """Determine if an error is transient and should be retried."""
    if isinstance(error, (ConnectionError, Timeout)):
        return True
    if isinstance(error, HTTPError) and error.response is not None:
        return 500 <= error.response.status_code < 600
    return False


def _is_retryable_response(response: requests.Response) -> bool:
    """Determine if a response indicates a transient error that should be retried."""
    return 500 <= response.status_code < 600


def supabase_request(
    method: str,
    path: str,
    timeout: Optional[int] = None,
    max_retries: Optional[int] = None,
    raise_on_error: bool = False,
    **kwargs: Any
) -> requests.Response:
    """
    Make a request to Supabase with retry logic and error handling.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        path: API path (e.g., /rest/v1/users)
        timeout: Request timeout in seconds (default: SUPABASE_TIMEOUT env var or 60)
        max_retries: Maximum number of retries for transient errors (default: SUPABASE_MAX_RETRIES or 3)
        raise_on_error: If True, raise exceptions for 4xx/5xx responses. If False (default),
                       return the response and let caller handle status codes. This maintains
                       backward compatibility with existing code.
        **kwargs: Additional arguments passed to requests.request()

    Returns:
        requests.Response object

    Raises:
        SupabaseConfigError: If Supabase configuration is missing
        SupabaseConnectionError: If unable to connect to Supabase after retries
        SupabaseTimeoutError: If request times out after retries
        SupabaseServerError: If Supabase returns a 5xx error after retries (only if raise_on_error=True)
        SupabaseClientError: If Supabase returns a 4xx error (only if raise_on_error=True)
        SupabaseError: For other unexpected errors
    """
    ensure_supabase_env()
    
    url = f"{SUPABASE_URL}{path}"
    headers = kwargs.pop("headers", {})
    merged_headers = {**supabase_headers(), **headers}
    request_timeout = timeout if timeout is not None else DEFAULT_TIMEOUT
    retries = max_retries if max_retries is not None else MAX_RETRIES
    
    last_error: Optional[Exception] = None
    last_response: Optional[requests.Response] = None
    
    for attempt in range(retries + 1):
        try:
            logger.debug(
                f"Supabase request attempt {attempt + 1}/{retries + 1}: {method.upper()} {path}"
            )
            
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=merged_headers,
                timeout=request_timeout,
                **kwargs,
            )
            
            if _is_retryable_response(response):
                last_response = response
                if attempt < retries:
                    backoff = INITIAL_BACKOFF * (2 ** attempt)
                    logger.warning(
                        f"Supabase returned {response.status_code}, retrying in {backoff:.1f}s "
                        f"(attempt {attempt + 1}/{retries + 1})"
                    )
                    time.sleep(backoff)
                    continue
                else:
                    logger.error(
                        f"Supabase request failed after {retries + 1} attempts: "
                        f"{method.upper()} {path} returned {response.status_code}"
                    )
                    if raise_on_error:
                        raise SupabaseServerError(
                            f"Supabase server error: {response.status_code}",
                            status_code=response.status_code
                        )
                    return response
            
            if 400 <= response.status_code < 500:
                logger.debug(
                    f"Supabase client response: {method.upper()} {path} returned {response.status_code}"
                )
                if raise_on_error:
                    raise SupabaseClientError(
                        f"Supabase client error: {response.status_code}",
                        status_code=response.status_code,
                        response_body=response.text
                    )
                return response
            
            logger.debug(f"Supabase request successful: {method.upper()} {path}")
            return response
            
        except ConnectionError as e:
            last_error = e
            if attempt < retries:
                backoff = INITIAL_BACKOFF * (2 ** attempt)
                logger.warning(
                    f"Connection error to Supabase, retrying in {backoff:.1f}s "
                    f"(attempt {attempt + 1}/{retries + 1}): {e}"
                )
                time.sleep(backoff)
            else:
                logger.error(
                    f"Failed to connect to Supabase after {retries + 1} attempts: {e}"
                )
                raise SupabaseConnectionError(
                    f"Failed to connect to Supabase after {retries + 1} attempts",
                    original_error=e
                ) from e
                
        except Timeout as e:
            last_error = e
            if attempt < retries:
                backoff = INITIAL_BACKOFF * (2 ** attempt)
                logger.warning(
                    f"Supabase request timed out, retrying in {backoff:.1f}s "
                    f"(attempt {attempt + 1}/{retries + 1}): {e}"
                )
                time.sleep(backoff)
            else:
                logger.error(
                    f"Supabase request timed out after {retries + 1} attempts: {e}"
                )
                raise SupabaseTimeoutError(
                    f"Supabase request timed out after {retries + 1} attempts",
                    original_error=e
                ) from e
                
        except (SupabaseClientError, SupabaseServerError, SupabaseConfigError):
            raise
            
        except RequestException as e:
            logger.error(f"Unexpected request error to Supabase: {e}")
            raise SupabaseError(
                f"Unexpected error making request to Supabase: {e}",
                original_error=e
            ) from e
            
        except Exception as e:
            logger.error(f"Unexpected error in Supabase request: {e}")
            raise SupabaseError(
                f"Unexpected error: {e}",
                original_error=e
            ) from e
    
    if last_response is not None:
        raise SupabaseServerError(
            f"Supabase server error after {retries + 1} attempts",
            status_code=last_response.status_code
        )
    elif last_error is not None:
        raise SupabaseError(
            f"Supabase request failed after {retries + 1} attempts",
            original_error=last_error
        )
    else:
        raise SupabaseError("Supabase request failed unexpectedly")


def check_connection(timeout: Optional[int] = None) -> bool:
    """
    Test if Supabase is reachable.

    Args:
        timeout: Request timeout in seconds (default: 10 seconds for health check)

    Returns:
        True if Supabase is reachable, False otherwise
    """
    if not supabase_configured():
        logger.warning("Supabase is not configured, cannot check connection")
        return False
    
    check_timeout = timeout if timeout is not None else 10
    
    try:
        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/",
            headers=supabase_headers(),
            timeout=check_timeout
        )
        is_reachable = response.status_code < 500
        if is_reachable:
            logger.debug("Supabase connection check successful")
        else:
            logger.warning(f"Supabase connection check failed with status {response.status_code}")
        return is_reachable
    except (ConnectionError, Timeout) as e:
        logger.warning(f"Supabase connection check failed: {e}")
        return False
    except RequestException as e:
        logger.warning(f"Supabase connection check failed with unexpected error: {e}")
        return False
