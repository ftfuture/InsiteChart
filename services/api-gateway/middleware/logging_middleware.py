"""Request/response logging middleware."""

import logging
import time
import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import json

logger = logging.getLogger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add unique request ID to each request."""

    async def dispatch(self, request: Request, call_next):
        """Add request ID to request and response.

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            Response with request ID header
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Add request ID to response headers
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for detailed request/response logging."""

    def __init__(self, app, logger_instance=None):
        """Initialize logging middleware.

        Args:
            app: FastAPI application
            logger_instance: Logger instance (optional)
        """
        super().__init__(app)
        self.logger = logger_instance or logging.getLogger(__name__)

    async def dispatch(self, request: Request, call_next):
        """Log request and response details.

        Args:
            request: HTTP request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        # Get request ID from request state
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))

        # Record request details
        method = request.method
        path = request.url.path
        query_string = request.url.query

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Get user agent
        user_agent = request.headers.get("user-agent", "unknown")

        # Get user from token if available
        user = getattr(request.state, "user", "anonymous")

        # Record start time
        start_time = time.time()

        # Log incoming request
        self.logger.info(
            f"[{request_id}] Incoming request: {method} {path} "
            f"from {client_ip} (user: {user})"
        )

        try:
            # Process request
            response = await call_next(request)

            # Record response time
            process_time = time.time() - start_time

            # Log response
            self.logger.info(
                f"[{request_id}] Response: {response.status_code} "
                f"in {process_time*1000:.2f}ms for {method} {path}"
            )

            # Add timing header
            response.headers["X-Process-Time"] = str(process_time)

            # Store metrics in request state for later access
            request.state.response_time = process_time
            request.state.status_code = response.status_code

            return response

        except Exception as e:
            # Record error time
            process_time = time.time() - start_time

            # Log error
            self.logger.error(
                f"[{request_id}] Error processing request: {str(e)} "
                f"in {process_time*1000:.2f}ms for {method} {path}"
            )

            # Re-raise exception
            raise


class AuditLogger:
    """Audit logger for important security events."""

    def __init__(self, logger_instance=None):
        """Initialize audit logger.

        Args:
            logger_instance: Logger instance (optional)
        """
        self.logger = logger_instance or logging.getLogger("audit")

    def log_authentication(
        self,
        username: str,
        success: bool,
        ip_address: str,
        request_id: str
    ):
        """Log authentication event.

        Args:
            username: Username
            success: Whether authentication was successful
            ip_address: Client IP address
            request_id: Request ID
        """
        status = "success" if success else "failed"
        self.logger.warning(
            f"[AUDIT] Authentication {status} for user '{username}' "
            f"from {ip_address} (request_id: {request_id})"
        )

    def log_rate_limit_exceeded(
        self,
        user: str,
        ip_address: str,
        limit_type: str,
        request_id: str
    ):
        """Log rate limit exceeded event.

        Args:
            user: User identifier
            ip_address: Client IP address
            limit_type: Type of limit (minute, hour, day)
            request_id: Request ID
        """
        self.logger.warning(
            f"[AUDIT] Rate limit exceeded ({limit_type}) for user '{user}' "
            f"from {ip_address} (request_id: {request_id})"
        )

    def log_access_denial(
        self,
        user: str,
        ip_address: str,
        reason: str,
        request_id: str
    ):
        """Log access denial event.

        Args:
            user: User identifier
            ip_address: Client IP address
            reason: Reason for denial
            request_id: Request ID
        """
        self.logger.warning(
            f"[AUDIT] Access denied for user '{user}' from {ip_address}: {reason} "
            f"(request_id: {request_id})"
        )

    def log_error(
        self,
        error_code: str,
        error_message: str,
        user: str,
        ip_address: str,
        request_id: str
    ):
        """Log error event.

        Args:
            error_code: Error code
            error_message: Error message
            user: User identifier
            ip_address: Client IP address
            request_id: Request ID
        """
        self.logger.error(
            f"[AUDIT] Error {error_code}: {error_message} "
            f"(user: '{user}', ip: {ip_address}, request_id: {request_id})"
        )


# Global audit logger instance
_audit_logger = None


def get_audit_logger() -> AuditLogger:
    """Get global audit logger instance.

    Returns:
        AuditLogger instance
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
