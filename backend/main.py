from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import engine, Base
from app.models import RawEvent, FactSubscription  
from app.api import events_router, kpis_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Event Ingestion & Analytics API",
    description="Sistema de ingestión de eventos y análisis de KPIs para múltiples dominios (subscriptions, orders, iot, notifications)",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events_router)
app.include_router(kpis_router)


@app.get("/", tags=["health"])
async def root():
    return {"message": "Event Ingestion & Analytics API is running", "status": "healthy"}
