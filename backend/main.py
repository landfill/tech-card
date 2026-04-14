"""FastAPI app and startup observability."""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.paths import get_config_dir, get_data_dir
from backend.routers import letters, feedback, pipeline, evolution, weekly

logger = logging.getLogger(__name__)


class SuppressStatusPollFilter(logging.Filter):
    """Suppress noisy polling access logs for the pipeline status endpoint only."""

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args if isinstance(record.args, tuple) else ()
        path = args[2] if len(args) >= 3 else ""
        if not isinstance(path, str):
            return True
        target = path.split("?", 1)[0]
        return target != "/api/pipeline/status"


def _configure_access_log_filter() -> None:
    access_logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(filt, SuppressStatusPollFilter) for filt in access_logger.filters):
        access_logger.addFilter(SuppressStatusPollFilter())


def build_startup_summary() -> str:
    root = Path(__file__).resolve().parent.parent
    env_file = root / ".env"
    data_dir = get_data_dir()
    config_dir = get_config_dir()
    smtp_configured = bool(os.environ.get("SMTP_USER", "").strip())
    google_api_key_set = bool(os.environ.get("GOOGLE_API_KEY", "").strip())
    return (
        "event=server_started "
        f"env_file_present={env_file.is_file()} "
        f"data_dir={data_dir} "
        f"config_dir={config_dir} "
        f"smtp_configured={smtp_configured} "
        f"google_api_key_set={google_api_key_set} "
        "routes=/api/letters,/api/pipeline,/api/weekly "
        "/api/pipeline/status access log suppressed"
    )


_configure_access_log_filter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if getattr(app.state, "startup_summary_logged", False):
        yield
        return
    logger.info(build_startup_summary())
    app.state.startup_summary_logged = True
    yield


app = FastAPI(title="Daily Intelligence Newsletter API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(letters.router, prefix="/api/letters", tags=["letters"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(evolution.router, prefix="/api/evolution", tags=["evolution"])
app.include_router(weekly.router, prefix="/api/weekly", tags=["weekly"])
