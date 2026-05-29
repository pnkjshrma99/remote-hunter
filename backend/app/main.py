import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import get_settings
from app.database import init_db
from app.tasks.scheduler import start_scheduler, stop_scheduler
from app.services.monitoring import get_monitoring_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    start_scheduler()
    
    # Start monitoring service
    monitoring = get_monitoring_service()
    monitoring.start_metrics_server()
    
    yield
    stop_scheduler()


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
cors_origin_regex = r"chrome-extension://.*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list if not settings.cors_allow_any_origin else ["*"],
    allow_origin_regex=cors_origin_regex,
    allow_credentials=not settings.cors_allow_any_origin,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}
