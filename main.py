""" FastAPI app for the user service. """

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from assets import download, upload
from commons import create_log_file, logger
from interview.routes import manage, streaming
from meta_data import routes as meta_data_routes
from reporting import routes as reporting_routes
from user_management.routes import admin, auth

create_log_file("interview_agent")

app = FastAPI()


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler."""
    logger.exception("Unhandled error: %s - %s", exc, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )


class WebSocketCORSMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling CORS preflight requests for WebSocket connections.

    This middleware adds the 'Access-Control-Allow-Origin' header to the WebSocket
    request if the 'Origin' header is present in the request headers. This is necessary
    to allow cross-origin WebSocket connections.

    Methods:
        dispatch(request, call_next): Asynchronously handles the incoming request and
        modifies the headers for WebSocket connections to include CORS headers if needed.
    """

    async def dispatch(self, request, call_next):
        if "websocket" in request.scope["type"]:
            if "origin" in request.headers:
                request.scope["headers"].append(
                    (b"Access-Control-Allow-Origin", request.headers["origin"].encode())
                )
        return await call_next(request)


# Set up CORS middleware options
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1",
        "http://admin.cwai.ykinnosoft.in",
        "http://admin.cwai.ykinnosoft.in/auth/sign-in",
        "http://candidate.cwai.ykinnosoft.in/auth/sign-in",
        "http://candidate.cwai.ykinnosoft.in",
        "https://admin.cwai.ykinnosoft.in",
        "https://admin.cwai.ykinnosoft.in/auth/sign-in",
        "https://candidate.cwai.ykinnosoft.in/auth/sign-in",
        "https://candidate.cwai.ykinnosoft.in",
    ],  # Allows all origins
    # allow_origins=["*"],  # This allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
app.add_middleware(SessionMiddleware, secret_key="some-random-secret-key")
app.add_middleware(WebSocketCORSMiddleware)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(upload.router)
app.include_router(download.router)
app.include_router(manage.router)
app.include_router(reporting_routes.router)
app.include_router(streaming.router)
app.include_router(meta_data_routes.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
    # uvicorn main:app --ssl-keyfile path/to/key.pem --ssl-certfile path/to/cert.pem
