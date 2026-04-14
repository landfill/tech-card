"""FastAPI app and startup observability."""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.paths import get_config_dir, get_data_dir
from backend.routers import letters, feedback, pipeline, evolution, weekly
from pipeline.llm.config import load_llm_config

logger = logging.getLogger(__name__)


class SuppressStatusPollFilter(logging.Filter):
    """Suppress noisy polling access logs for the pipeline status endpoint only."""

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args if isinstance(record.args, tuple) else ()
        method = args[1] if len(args) >= 2 else ""
        path = args[2] if len(args) >= 3 else ""
        status_code = args[4] if len(args) >= 5 else 0
        if not isinstance(path, str):
            return True
        target = path.split("?", 1)[0]
        if method not in {"GET", "OPTIONS"}:
            return True
        if isinstance(status_code, int) and status_code >= 400:
            return True
        if target == "/api/pipeline/status":
            return False
        if target.startswith("/api/letters"):
            return False
        if target.startswith("/api/weekly"):
            return False
        return True


def _configure_application_logging() -> None:
    root_logger = logging.getLogger()
    uvicorn_error = logging.getLogger("uvicorn.error")
    candidate_handlers = uvicorn_error.handlers or []
    for handler in candidate_handlers:
        if handler not in root_logger.handlers:
            root_logger.addHandler(handler)
    if not root_logger.handlers:
        root_logger.addHandler(logging.StreamHandler())
    if root_logger.level == logging.NOTSET or root_logger.level > logging.INFO:
        root_logger.setLevel(logging.INFO)
    for logger_name in ("backend", "pipeline", "tools"):
        app_logger = logging.getLogger(logger_name)
        app_logger.setLevel(logging.INFO)
        app_logger.propagate = True
    for noisy_logger_name in ("httpx", "httpcore", "openai", "openai._base_client"):
        noisy_logger = logging.getLogger(noisy_logger_name)
        noisy_logger.setLevel(logging.WARNING)
        noisy_logger.propagate = True


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
    openai_api_key_set = bool(os.environ.get("OPENAI_API_KEY", "").strip())
    llm_config_path = config_dir / "llm.yaml"
    if not llm_config_path.is_file():
        llm_config_path = config_dir / "llm.yaml.example"
    llm_provider = "unknown"
    llm_model = "unknown"
    if llm_config_path.is_file():
        try:
            llm_cfg = load_llm_config(llm_config_path)
            llm_provider = llm_cfg["provider"]
            llm_model = llm_cfg["model"]
        except Exception:
            pass
    return (
        "event=server_started "
        f"env_file_present={env_file.is_file()} "
        f"data_dir={data_dir} "
        f"config_dir={config_dir} "
        f"smtp_configured={smtp_configured} "
        f"google_api_key_set={google_api_key_set} "
        f"openai_api_key_set={openai_api_key_set} "
        f"llm_provider={llm_provider} "
        f"llm_model={llm_model} "
        "routes=/api/letters,/api/pipeline,/api/weekly "
        "noisy_ui_access_logs_suppressed=/api/letters,/api/weekly,/api/pipeline/status"
    )


_configure_application_logging()
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
