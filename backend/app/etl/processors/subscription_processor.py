from datetime import datetime, date, timezone
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models import RawEvent, FactSubscription


class PayloadValidationError(Exception):
    pass


def _validate_payload(payload: Dict[str, Any]) -> None:
    if "contract_id" not in payload or payload["contract_id"] is None:
        raise PayloadValidationError(
            "Campo requerido faltante: contract_id"
        )


def _map_event_type_to_flags(event_type: str) -> Dict[str, bool]:
    flags = {}

    if event_type == "renewal_success":
        flags["renewed"] = True
    elif event_type == "renewal_failed":
        flags["renewed"] = False
    elif event_type == "payment_success":
        flags["billing_success"] = True
    elif event_type == "payment_failed":
        flags["billing_success"] = False

    return flags


def process_subscription_event(db: Session, raw_event: RawEvent) -> Optional[FactSubscription]:

    try:
        payload = raw_event.payload or {}
        _validate_payload(payload)

        contract_id = str(payload.get("contract_id"))

        existing = db.query(FactSubscription).filter(
            FactSubscription.contract_id == contract_id
        ).first()

        if existing:
            fact_sub = existing
        else:
            user_id = payload.get("user_id")
            plan_id = payload.get("plan_id")
            if user_id is None:
                raise PayloadValidationError("Campo requerido faltante: user_id")
            if plan_id is None:
                raise PayloadValidationError("Campo requerido faltante: plan_id")

            start_date = payload.get("start_date")
            if start_date and isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date).date()
            else:
                start_date = datetime.now(tz=timezone.utc).date()

            status = payload.get("status", "active")

            fact_sub = FactSubscription(
                contract_id=contract_id,
                user_id=user_id,
                plan_id=plan_id,
                status=status.lower() if isinstance(status, str) else status,
                start_date=start_date,
                created_at=datetime.now(tz=timezone.utc),
                updated_at=datetime.now(tz=timezone.utc)
            )
            db.add(fact_sub)

        if raw_event.event_type == "subscription_created":
            fact_sub.renewed = raw_event.payload.get("renewed", False)
            fact_sub.auto_service = raw_event.payload.get("auto_service", False)
            fact_sub.billing_success = raw_event.payload.get("billing_success", False)

            if "status" in raw_event.payload:
                status_val = raw_event.payload.get("status")
                fact_sub.status = status_val.lower() if isinstance(status_val, str) else status_val

            if "end_date" in raw_event.payload:
                end_date = raw_event.payload.get("end_date")
                if end_date and isinstance(end_date, str):
                    fact_sub.end_date = datetime.fromisoformat(end_date).date()
                else:
                    fact_sub.end_date = end_date
        else:
            flags = _map_event_type_to_flags(raw_event.event_type)
            for flag_name, flag_value in flags.items():
                if hasattr(fact_sub, flag_name):
                    setattr(fact_sub, flag_name, flag_value)

        if raw_event.event_type in ["payment_success", "payment_failed"]:
            fact_sub.billing_date = datetime.now(tz=timezone.utc)
            fact_sub.billing_attempts = (fact_sub.billing_attempts or 0) + 1

        fact_sub.updated_at = datetime.now(tz=timezone.utc)

        db.add(fact_sub)
        db.flush()

        return fact_sub

    except PayloadValidationError:
        raise

    except SQLAlchemyError:
        raise

    except Exception:
        raise