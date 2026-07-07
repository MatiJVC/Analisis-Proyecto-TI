"""
Tests para Subscription ETL processor.
"""

import pytest
from datetime import datetime, date, timezone
from unittest.mock import MagicMock

from app.etl.processors.subscription_processor import (
    process_subscription_event,
    PayloadValidationError
)
from app.models import FactSubscription


def _make_raw(event_type: str, payload: dict):
    raw = MagicMock()
    raw.event_type = event_type
    raw.payload = payload
    return raw


def _make_db(existing=None):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = existing
    return db


class TestSubscriptionETL:
    def test_subscription_created_creates_new(self):
        db = _make_db(None)
        raw = _make_raw(
            "subscription_created",
            {
                "contract_id": "CTR-1234",
                "plan_id": 2,
                "user_id": 99,
                "status": "ACTIVE",
                "start_date": "2026-07-07",
                "renewed": True,
                "auto_service": True,
                "billing_success": True
            }
        )
        fact = process_subscription_event(db, raw)
        assert fact is not None
        assert fact.contract_id == "CTR-1234"
        assert fact.user_id == "99"
        assert fact.plan_id == 2
        assert fact.status == "active"
        assert fact.start_date == date(2026, 7, 7)
        assert fact.renewed is True
        assert fact.auto_service is True
        assert fact.billing_success is True
        db.add.assert_called()

    def test_subscription_created_uuid_user_id(self):
        db = _make_db(None)
        raw = _make_raw(
            "subscription_created",
            {
                "contract_id": "CTR-1234",
                "plan_id": 2,
                "user_id": "a15b2f00-26a5-474c-b530-d0f6824558b2",
                "status": "ACTIVE",
                "start_date": "2026-07-07"
            }
        )
        fact = process_subscription_event(db, raw)
        assert fact is not None
        assert fact.user_id == "a15b2f00-26a5-474c-b530-d0f6824558b2"

    def test_subscription_created_missing_user_id_is_ok(self):
        # We made user_id optional!
        db = _make_db(None)
        raw = _make_raw(
            "subscription_created",
            {
                "contract_id": "CTR-1234",
                "plan_id": 2,
                "status": "ACTIVE",
                "start_date": "2026-07-07"
            }
        )
        fact = process_subscription_event(db, raw)
        assert fact is not None
        assert fact.user_id is None

    def test_subscription_created_missing_plan_id_raises(self):
        db = _make_db(None)
        raw = _make_raw(
            "subscription_created",
            {
                "contract_id": "CTR-1234",
                "user_id": 99,
                "status": "ACTIVE"
            }
        )
        with pytest.raises(PayloadValidationError):
            process_subscription_event(db, raw)

    def test_subscription_cancelled_updates_existing(self):
        existing = FactSubscription(
            contract_id="CTR-1234",
            user_id="99",
            plan_id=2,
            status="active",
            start_date=date(2026, 7, 7)
        )
        db = _make_db(existing)
        raw = _make_raw(
            "subscription_cancelled",
            {
                "contract_id": "CTR-1234",
                "cancelled_at": "2026-07-15T12:00:00.000Z"
            }
        )
        fact = process_subscription_event(db, raw)
        assert fact is not None
        assert fact.status == "cancelled"
        assert fact.end_date == date(2026, 7, 15)

    def test_subscription_cancelled_default_end_date(self):
        existing = FactSubscription(
            contract_id="CTR-1234",
            user_id="99",
            plan_id=2,
            status="active",
            start_date=date(2026, 7, 7)
        )
        db = _make_db(existing)
        raw = _make_raw(
            "subscription_cancelled",
            {
                "contract_id": "CTR-1234"
            }
        )
        fact = process_subscription_event(db, raw)
        assert fact is not None
        assert fact.status == "cancelled"
        assert fact.end_date == datetime.now(tz=timezone.utc).date()

    def test_renewal_success_updates_flags(self):
        existing = FactSubscription(
            contract_id="CTR-1234",
            user_id="99",
            plan_id=2,
            status="active",
            start_date=date(2026, 7, 7),
            renewed=False
        )
        db = _make_db(existing)
        raw = _make_raw(
            "renewal_success",
            {
                "contract_id": "CTR-1234"
            }
        )
        fact = process_subscription_event(db, raw)
        assert fact is not None
        assert fact.renewed is True
