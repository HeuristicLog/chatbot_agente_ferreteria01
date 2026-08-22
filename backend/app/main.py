import os
import time
import logging
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db.base import Base
from app.db.session import engine
from app.api import health, tools, webhooks, testing, admin, logistics_mock, admin_api, agent_api, chat_api

# Initialize logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("backend")

# Set timezone
os.environ["TZ"] = settings.APP_TIMEZONE
try:
    time.tzset()
except AttributeError:
    # Windows doesn't support tzset
    pass

app = FastAPI(
    title="Ferreteria Chatbot Backend Integration",
    version="2.0.0",
    description="Primary API gateway and integration layer between WhatsApp, Flowise, Qdrant, and Postgres."
)

# CORS config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Startup DB Initialisation
@app.on_event("startup")
async def startup_db():
    logger.info("Initializing PostgreSQL database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables verified.")

# Global exception handlers for standard envelope response
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("An unhandled exception occurred:")
    import uuid
    request_id = str(uuid.uuid4())
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "message": "No fue posible procesar tu solicitud en este momento.",
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "details": str(exc)
            },
            "correlation_id": request_id
        }
    )

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(tools.router, tags=["Flowise Tools Legacy"])
app.include_router(webhooks.router, tags=["Webhooks"])
app.include_router(testing.router, tags=["Testing"])
app.include_router(admin.router, tags=["Admin Page Legacy"])
app.include_router(logistics_mock.router, tags=["Logistics Mock Legacy"])

# Include New Routers
app.include_router(admin_api.router, tags=["Admin Portal APIs"])
app.include_router(agent_api.router, tags=["Agent Console APIs"])
app.include_router(chat_api.router, tags=["Chat Façade APIs"])
