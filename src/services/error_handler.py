import traceback
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

def error_handler(app):
    """Register a simple error handling middleware for FastAPI apps.

    The function attaches a ``exception_handler`` that catches generic
    ``Exception`` instances and returns a JSON payload with a 500 status.
    ``HTTPException`` instances are passed through unchanged.
    """
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        # Log the traceback to the audit logger if available
        try:
            from src.services.logging_service import audit_logger
            audit_logger.log("exception", {"path": str(request.url), "error": str(exc)})
        except Exception:
            # Fallback to standard print if audit logger import fails
            print(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "error": str(exc)},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
