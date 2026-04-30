"""Public FastAPI app and startup observability."""
from backend.app_factory import (
    SuppressStatusPollFilter,
    _configure_access_log_filter,
    _configure_application_logging,
    build_startup_summary,
    create_app,
)
from backend.routers import feedback, letters, weekly

app = create_app(
    title="Daily Intelligence Newsletter Public API",
    app_role="public",
    route_labels=["/api/letters", "/api/feedback", "/api/weekly"],
    router_specs=[
        (letters.router, "/api/letters", ["letters"]),
        (feedback.router, "/api/feedback", ["feedback"]),
        (weekly.router, "/api/weekly", ["weekly"]),
    ],
)
