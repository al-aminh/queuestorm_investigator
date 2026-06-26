from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import router

app = FastAPI(
    title="QueueStorm Investigator",
    description="Deterministic evidence-first support copilot for digital finance tickets.",
    version="1.0.0",
)
app.include_router(router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Controlled, non-sensitive validation error; no stack traces or secrets.
    return JSONResponse(status_code=422, content={"error": "invalid_request", "detail": "Request body does not match the required schema."})


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": "request_error", "detail": str(exc.detail)})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"error": "internal_error", "detail": "A safe internal error occurred. Please retry or contact support."})
