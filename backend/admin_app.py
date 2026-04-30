"""Admin-only FastAPI app."""
from backend.app_factory import create_app
from backend.routers import evolution, pipeline
from backend.routers.letters import admin_router as admin_letters_router
from backend.routers.weekly import admin_router as admin_weekly_router

app = create_app(
    title="Daily Intelligence Newsletter Admin API",
    app_role="admin",
    route_labels=["/api/letters", "/api/weekly", "/api/pipeline", "/api/evolution"],
    router_specs=[
        (admin_letters_router, "/api/letters", ["letters-admin"]),
        (admin_weekly_router, "/api/weekly", ["weekly-admin"]),
        (pipeline.router, "/api/pipeline", ["pipeline"]),
        (evolution.router, "/api/evolution", ["evolution"]),
    ],
)
