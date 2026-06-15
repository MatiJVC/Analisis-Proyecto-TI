"""
Tests para la lógica de retry / dead-letter / concurrencia en _run_etl.

_run_etl abre su propia sesión DB vía SessionLocal(). Todos los tests
parchean app.api.routes.events.SessionLocal para inyectar un mock de sesión
sin necesitar una base de datos real.

Cubre:
  Éxito
    - processed = True, db.commit(), db.close()
  Retry increment
    - primer fallo → retry_count += 1, failed permanece False
    - fallo en retry_count == MAX_ETL_RETRIES - 1 → failed = True
    - retry_count ya en MAX_ETL_RETRIES → sigue marcando failed = True
  Skip conditions
    - evento ya processed → processor no llamado
    - evento ya failed → processor no llamado
    - raw_event no encontrado → processor no llamado
    - source desconocido → SessionLocal nunca abierta
  Concurrency guard (FOR UPDATE NOWAIT)
    - OperationalError → return sin incrementar retry_count
    - OperationalError → db.rollback() llamado
    - OperationalError → db.close() siempre llamado
"""
import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError

from app.api.routes.events import _run_etl, MAX_ETL_RETRIES


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _raw_event(*, processed=False, failed=False, retry_count=0):
    raw = MagicMock()
    raw.processed = processed
    raw.failed = failed
    raw.retry_count = retry_count
    return raw


def _make_session(raw_event=None, lock_contention=False):
    """
    Construye un mock de sesión compatible con los dos patrones de query en _run_etl:

      1. db.query(RawEvent).filter(...).with_for_update(nowait=True).first()
         → devuelve raw_event (o lanza OperationalError si lock_contention=True)
      2. db.query(RawEvent).filter(...).first()
         → devuelve raw_event (path de actualización de retry_count)
    """
    db = MagicMock()
    filt = db.query.return_value.filter.return_value

    if lock_contention:
        def _raise_lock(*args, **kwargs):
            raise OperationalError(
                "could not obtain lock on row in relation",
                {},
                Exception("pg lock"),
            )
        filt.with_for_update.return_value.first.side_effect = _raise_lock
    else:
        filt.with_for_update.return_value.first.return_value = raw_event

    # Path sin with_for_update — usado en el bloque de actualización de retry_count
    filt.first.return_value = raw_event
    return db


def _failing_processor(exc=None):
    p = MagicMock(side_effect=exc or RuntimeError("processor boom"))
    return p


# ─── Éxito ───────────────────────────────────────────────────────────────────

class TestRunEtlSuccess:
    def test_sets_processed_true(self):
        raw = _raw_event()
        db = _make_session(raw_event=raw)

        with (
            patch("app.api.routes.events.SessionLocal", return_value=db),
            patch.dict("app.api.routes.events._ETL_PROCESSORS", {"orders": MagicMock()}),
        ):
            _run_etl(uuid.uuid4(), "orders")

        assert raw.processed is True

    def test_commits_exactly_once(self):
        raw = _raw_event()
        db = _make_session(raw_event=raw)

        with (
            patch("app.api.routes.events.SessionLocal", return_value=db),
            patch.dict("app.api.routes.events._ETL_PROCESSORS", {"orders": MagicMock()}),
        ):
            _run_etl(uuid.uuid4(), "orders")

        db.commit.assert_called_once()

    def test_closes_session(self):
        raw = _raw_event()
        db = _make_session(raw_event=raw)

        with (
            patch("app.api.routes.events.SessionLocal", return_value=db),
            patch.dict("app.api.routes.events._ETL_PROCESSORS", {"orders": MagicMock()}),
        ):
            _run_etl(uuid.uuid4(), "orders")

        db.close.assert_called_once()

    def test_processor_receives_raw_event(self):
        raw = _raw_event()
        db = _make_session(raw_event=raw)
        processor = MagicMock()

        with (
            patch("app.api.routes.events.SessionLocal", return_value=db),
            patch.dict("app.api.routes.events._ETL_PROCESSORS", {"orders": processor}),
        ):
            _run_etl(uuid.uuid4(), "orders")

        processor.assert_called_once_with(db, raw)


# ─── Retry increment ──────────────────────────────────────────────────────────

class TestRetryIncrement:
    def test_first_failure_increments_retry_count_to_one(self):
        raw = _raw_event(retry_count=0)
        db = _make_session(raw_event=raw)

        with (
            patch("app.api.routes.events.SessionLocal", return_value=db),
            patch.dict("app.api.routes.events._ETL_PROCESSORS",
                       {"orders": _failing_processor()}),
        ):
            _run_etl(uuid.uuid4(), "orders")

        assert raw.retry_count == 1

    def test_failure_below_limit_does_not_dead_letter(self):
        raw = _raw_event(retry_count=2)
        db = _make_session(raw_event=raw)

        with (
            patch("app.api.routes.events.SessionLocal", return_value=db),
            patch.dict("app.api.routes.events._ETL_PROCESSORS",
                       {"orders": _failing_processor()}),
        ):
            _run_etl(uuid.uuid4(), "orders")

        assert raw.retry_count == 3
        assert raw.failed is False

    def test_failure_at_limit_sets_failed_true(self):
        """retry_count at MAX_ETL_RETRIES - 1: next failure must dead-letter the event."""
        raw = _raw_event(retry_count=MAX_ETL_RETRIES - 1)
        db = _make_session(raw_event=raw)

        with (
            patch("app.api.routes.events.SessionLocal", return_value=db),
            patch.dict("app.api.routes.events._ETL_PROCESSORS",
                       {"orders": _failing_processor()}),
        ):
            _run_etl(uuid.uuid4(), "orders")

        assert raw.retry_count == MAX_ETL_RETRIES
        assert raw.failed is True

    def test_failure_above_limit_also_sets_failed_true(self):
        raw = _raw_event(retry_count=MAX_ETL_RETRIES)
        db = _make_session(raw_event=raw)

        with (
            patch("app.api.routes.events.SessionLocal", return_value=db),
            patch.dict("app.api.routes.events._ETL_PROCESSORS",
                       {"orders": _failing_processor()}),
        ):
            _run_etl(uuid.uuid4(), "orders")

        assert raw.failed is True

    def test_failure_commits_retry_count_update(self):
        raw = _raw_event(retry_count=0)
        db = _make_session(raw_event=raw)

        with (
            patch("app.api.routes.events.SessionLocal", return_value=db),
            patch.dict("app.api.routes.events._ETL_PROCESSORS",
                       {"orders": _failing_processor()}),
        ):
            _run_etl(uuid.uuid4(), "orders")

        # One commit for the retry_count update (processed=True commit never runs)
        db.commit.assert_called_once()

    def test_failure_closes_session(self):
        raw = _raw_event(retry_count=0)
        db = _make_session(raw_event=raw)

        with (
            patch("app.api.routes.events.SessionLocal", return_value=db),
            patch.dict("app.api.routes.events._ETL_PROCESSORS",
                       {"orders": _failing_processor()}),
        ):
            _run_etl(uuid.uuid4(), "orders")

        db.close.assert_called_once()


# ─── Skip conditions ──────────────────────────────────────────────────────────

class TestSkipConditions:
    def test_already_processed_skips_processor(self):
        raw = _raw_event(processed=True)
        db = _make_session(raw_event=raw)
        processor = MagicMock()

        with (
            patch("app.api.routes.events.SessionLocal", return_value=db),
            patch.dict("app.api.routes.events._ETL_PROCESSORS", {"orders": processor}),
        ):
            _run_etl(uuid.uuid4(), "orders")

        processor.assert_not_called()

    def test_already_failed_skips_processor(self):
        raw = _raw_event(failed=True)
        db = _make_session(raw_event=raw)
        processor = MagicMock()

        with (
            patch("app.api.routes.events.SessionLocal", return_value=db),
            patch.dict("app.api.routes.events._ETL_PROCESSORS", {"orders": processor}),
        ):
            _run_etl(uuid.uuid4(), "orders")

        processor.assert_not_called()

    def test_event_not_found_skips_processor(self):
        db = _make_session(raw_event=None)
        processor = MagicMock()

        with (
            patch("app.api.routes.events.SessionLocal", return_value=db),
            patch.dict("app.api.routes.events._ETL_PROCESSORS", {"orders": processor}),
        ):
            _run_etl(uuid.uuid4(), "orders")

        processor.assert_not_called()

    def test_unknown_source_never_opens_session(self):
        """_ETL_PROCESSORS.get() returns None → return before SessionLocal() is called."""
        mock_session_factory = MagicMock()

        with patch("app.api.routes.events.SessionLocal", mock_session_factory):
            _run_etl(uuid.uuid4(), "fuente_inexistente")

        mock_session_factory.assert_not_called()


# ─── Concurrency guard (FOR UPDATE NOWAIT) ────────────────────────────────────

class TestConcurrencyGuard:
    """
    Si FOR UPDATE NOWAIT lanza OperationalError, otro worker ya tiene el lock.
    _run_etl debe saltar el evento sin incrementar retry_count ni marcar failed.
    """

    def test_lock_contention_does_not_increment_retry_count(self):
        raw = _raw_event(retry_count=0)
        db = _make_session(raw_event=raw, lock_contention=True)

        with (
            patch("app.api.routes.events.SessionLocal", return_value=db),
            patch.dict("app.api.routes.events._ETL_PROCESSORS", {"orders": MagicMock()}),
        ):
            _run_etl(uuid.uuid4(), "orders")

        assert raw.retry_count == 0

    def test_lock_contention_does_not_set_failed(self):
        raw = _raw_event()
        db = _make_session(raw_event=raw, lock_contention=True)

        with (
            patch("app.api.routes.events.SessionLocal", return_value=db),
            patch.dict("app.api.routes.events._ETL_PROCESSORS", {"orders": MagicMock()}),
        ):
            _run_etl(uuid.uuid4(), "orders")

        assert raw.failed is False

    def test_lock_contention_calls_rollback(self):
        db = _make_session(lock_contention=True)

        with (
            patch("app.api.routes.events.SessionLocal", return_value=db),
            patch.dict("app.api.routes.events._ETL_PROCESSORS", {"orders": MagicMock()}),
        ):
            _run_etl(uuid.uuid4(), "orders")

        db.rollback.assert_called()

    def test_lock_contention_closes_session(self):
        db = _make_session(lock_contention=True)

        with (
            patch("app.api.routes.events.SessionLocal", return_value=db),
            patch.dict("app.api.routes.events._ETL_PROCESSORS", {"orders": MagicMock()}),
        ):
            _run_etl(uuid.uuid4(), "orders")

        db.close.assert_called_once()

    def test_lock_contention_does_not_commit(self):
        db = _make_session(lock_contention=True)

        with (
            patch("app.api.routes.events.SessionLocal", return_value=db),
            patch.dict("app.api.routes.events._ETL_PROCESSORS", {"orders": MagicMock()}),
        ):
            _run_etl(uuid.uuid4(), "orders")

        db.commit.assert_not_called()
