from fastapi import APIRouter

from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.companies import router as companies_router
from app.api.cover_letters import router as cover_letters_router
from app.api.cv import router as cv_router
from app.api.job_bundles import router as job_bundles_router
from app.api.jobs import router as jobs_router
from app.api.learning_paths import router as learning_paths_router
from app.api.monitoring import router as monitoring_router
from app.api.saved_searches import router as saved_searches_router
from app.api.scrape_runs import router as scrape_runs_router
from app.api.source_health import router as source_health_router
from app.api.subscriptions import router as subscriptions_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(jobs_router)
api_router.include_router(cover_letters_router)
api_router.include_router(scrape_runs_router)
api_router.include_router(analytics_router)
api_router.include_router(companies_router)
api_router.include_router(saved_searches_router)
api_router.include_router(subscriptions_router)
api_router.include_router(learning_paths_router)
api_router.include_router(job_bundles_router)
api_router.include_router(source_health_router)
api_router.include_router(monitoring_router)
api_router.include_router(cv_router)