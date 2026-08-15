import asyncio
import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.db import close_database, initialize_database
from app.errors import (
    ConflictError,
    IntegrationUnavailableError,
    InvalidAttachmentError,
    ResourceNotFoundError,
)
from app.logging_config import bind_request_id, configure_logging, reset_request_id
from app.routes import ROUTERS
from app.services.gmail import gmail_polling_loop, stop_gmail_poller

settings = get_settings()
configure_logging(settings)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info(
        "application_start env=%s tracing=%s langsmith_project=%s",
        settings.app_env,
        settings.langsmith_tracing,
        settings.langsmith_project,
    )
    await initialize_database()
    logger.info("database_initialized")
    application.state.gmail_task = None
    if settings.gmail_enabled and settings.gmail_poller_in_api:
        application.state.gmail_task = asyncio.create_task(
            gmail_polling_loop(settings), name="gmail-poller"
        )
    yield
    await stop_gmail_poller(application.state.gmail_task)
    await close_database()
    logger.info("application_stopped")


def create_app() -> FastAPI:
    application = FastAPI(
        title="Purchase Order Intake Agent",
        version="0.3.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for router in ROUTERS:
        application.include_router(router)

    @application.exception_handler(ResourceNotFoundError)
    async def not_found_handler(_: Request, exc: ResourceNotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @application.exception_handler(ConflictError)
    async def conflict_handler(_: Request, exc: ConflictError):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @application.exception_handler(InvalidAttachmentError)
    async def invalid_attachment_handler(_: Request, exc: InvalidAttachmentError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @application.exception_handler(IntegrationUnavailableError)
    async def integration_handler(_: Request, exc: IntegrationUnavailableError):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @application.middleware("http")
    async def request_logging(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        token = bind_request_id(request_id)
        logger.info("request_started method=%s path=%s", request.method, request.url.path)
        try:
            response = await call_next(request)
            response.headers["x-request-id"] = request_id
            logger.info(
                "request_completed method=%s path=%s status=%s",
                request.method,
                request.url.path,
                response.status_code,
            )
            return response
        except Exception:
            logger.exception("request_failed method=%s path=%s", request.method, request.url.path)
            raise
        finally:
            reset_request_id(token)

    return application


app = create_app()
