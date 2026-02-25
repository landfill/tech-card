"""FastAPI 앱. 발송 내역·피드백 API."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import letters, feedback

app = FastAPI(title="Daily Intelligence Newsletter API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(letters.router, prefix="/api/letters", tags=["letters"])
app.include_router(feedback.router, prefix="/api/feedback", tags=["feedback"])
