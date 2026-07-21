import logging
import sys
from loguru import logger
from app.config.settings import get_settings


class InterceptHandler(logging.Handler):
    """
    Intercept standard Python logging calls (Uvicorn, FastAPI, LangGraph)
    and redirect them to Loguru safely.
    """

    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Safely find caller frame to report accurate line numbers
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    """Configures centralized logging for local dev and production JSON."""
    settings = get_settings()

    # Clear standard loguru handlers
    logger.remove()

    # Determine format based on environment
    if settings.app_env.lower() == "production":
        # Structured JSON logging for production (Datadog, CloudWatch, Grafana)
        logger.add(
            sys.stdout,
            level=settings.log_level.upper(),
            serialize=True,
            backtrace=False,
            diagnose=False,
        )
    else:
        # Colored human-readable console output for local development
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level:8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )
        logger.add(
            sys.stderr,
            level=settings.log_level.upper(),
            format=log_format,
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

    # Intercept all python logging messages from dependencies (uvicorn, fastapi, langgraph)
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for logger_name in ("uvicorn", "uvicorn.access", "fastapi"):
        mod_logger = logging.getLogger(logger_name)
        mod_logger.handlers = [InterceptHandler()]


# Instantiate standard app logger export
app_logger = logger