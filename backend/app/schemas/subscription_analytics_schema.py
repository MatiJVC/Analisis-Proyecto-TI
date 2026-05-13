from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import date


class SubscriptionTimelinePoint(BaseModel):
    """Punto en el timeline de suscripciones"""
    date: str
    new_subscriptions: int
    renewals: int
    cancellations: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2026-05-13",
                "new_subscriptions": 15,
                "renewals": 8,
                "cancellations": 2
            }
        }


class SubscriptionTimelineResponse(BaseModel):
    """Respuesta con timeline de suscripciones"""
    start_date: str
    end_date: str
    total_subscriptions: int
    timeline: List[SubscriptionTimelinePoint]
    
    class Config:
        json_schema_extra = {
            "example": {
                "start_date": "2026-04-13",
                "end_date": "2026-05-13",
                "total_subscriptions": 250,
                "timeline": [
                    {
                        "date": "2026-05-13",
                        "new_subscriptions": 15,
                        "renewals": 8,
                        "cancellations": 2
                    },
                    {
                        "date": "2026-05-12",
                        "new_subscriptions": 12,
                        "renewals": 5,
                        "cancellations": 1
                    }
                ]
            }
        }
