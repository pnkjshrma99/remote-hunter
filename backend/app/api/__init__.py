from fastapi import APIRouter

from app.api.cover_letters import router as cover_letters_router
from app.api.jobs import router as jobs_router
from app.api.scrape_runs import router as scrape_runs_router

api_router = APIRouter()
api_router.include_router(jobs_router)
api_router.include_router(cover_letters_router)
api_router.include_router(scrape_runs_router)
