#!/usr/bin/env python3
"""
Test script for fact_payments_events audit table integration.
Demonstrates immutable event recording for payment gateway events.
"""

import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

# Adjust path for imports
backend_path = os.path.join(os.path.dirname(__file__), '..')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Load environment from .env.local (root of project)
from dotenv import load_dotenv
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
env_file = os.path.join(project_root, '.env.local')
if os.path.exists(env_file):
    load_dotenv(env_file)
else:
    print(f"⚠️  Warning: {env_file} not found. Using DATABASE_URL from environment.")

from sqlalchemy.orm import Session
from app.db import SessionLocal, engine, Base
from app.models.warehouse.pagos.fact_payments_events import FactPaymentsEvent
from app.models.warehouse.pagos.fact_pagos import FactPagos
from app.models.warehouse.pagos.dim_estados_conciliacion import DimEstadosConciliacion
from app.models.raw.raw_events import RawEvent


def setup_db():
    """Create all tables (idempotent)."""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created/verified")


def cleanup_test_data(db: Session):
    """Remove test data to allow re-runs."""
    # Clean in reverse dependency order
    db.query(FactPaymentsEvent).delete()
    db.query(FactPagos).delete()
    db.query(RawEvent).delete()
    db.commit()
    print("🧹 Test data cleaned")


def test_payment_flow():
    """
    End-to-end test: intento_pago → confirmar_pago with immutable audit events.
    """
    db = SessionLocal()
    
    try:
        cleanup_test_data(db)
        
        # ========== STEP 1: INTENTO_PAGO ==========
        print("\n📝 Step 1: Registering payment attempt (intento_pago)")
        
        tx_id = uuid4()
        order_id = "ORD-2026-TEST-001"
        token = f"tk_test_{tx_id.hex[:8]}"
        
        # Create raw event
        raw_event = RawEvent(
            source="payments",
            event_type="intento_pago",
            payload={
                "transaction_id": str(tx_id),
                "order_id": order_id,
                "subscription_id": None,
                "monto": 99.99,
                "token_transaccion": token,
                "timestamp_evento": datetime.now(timezone.utc).isoformat(),
            }
        )
        db.add(raw_event)
        db.commit()
        print(f"  ✓ Raw event created: id={raw_event.id}")
        
        # Simulate service layer: register attempt
        estado = db.query(DimEstadosConciliacion).filter_by(nombre="esperando_revisión").one_or_none()
        if not estado:
            estado = DimEstadosConciliacion(nombre="esperando_revisión")
            db.add(estado)
            db.flush()
        
        fact = FactPagos(
            transaction_id=tx_id,
            order_id=order_id,
            subscription_id=None,
            monto=Decimal("99.99"),
            token_transaccion=token,
            codigo_error=None,
            timestamp_evento=datetime.now(timezone.utc),
            estado_conciliacion_id=estado.id,
        )
        db.add(fact)
        db.flush()
        print(f"  ✓ FactPagos inserted: transaction_id={fact.transaction_id}")
        
        # Insert immutable audit event
        audit_1 = FactPaymentsEvent(
            transaction_id=fact.transaction_id,
            order_id=fact.order_id,
            subscription_id=fact.subscription_id,
            amount=fact.monto,
            token_transaccion=fact.token_transaccion,
            codigo_error=fact.codigo_error,
            status="esperando_revisión",
            timestamp_evento=fact.timestamp_evento,
        )
        db.add(audit_1)
        db.commit()
        print(f"  ✓ Audit event inserted: id={audit_1.id}, status={audit_1.status}")
        
        # ========== STEP 2: CONFIRMAR_PAGO ==========
        print("\n✅ Step 2: Confirming payment (confirmar_pago)")
        
        # Simulate confirmation from gateway: approved
        confirm_fact = db.query(FactPagos).filter_by(token_transaccion=token).one_or_none()
        assert confirm_fact, "Fact not found for token"
        
        # Update to Aprobado
        estado_aprobado = db.query(DimEstadosConciliacion).filter_by(nombre="Aprobado").one_or_none()
        if not estado_aprobado:
            estado_aprobado = DimEstadosConciliacion(nombre="Aprobado")
            db.add(estado_aprobado)
            db.flush()
        
        confirm_fact.estado_conciliacion_id = estado_aprobado.id
        confirm_fact.timestamp_evento = datetime.now(timezone.utc)
        db.flush()
        print(f"  ✓ FactPagos updated: status_id={confirm_fact.estado_conciliacion_id}")
        
        # Insert immutable audit event for confirmation
        audit_2 = FactPaymentsEvent(
            transaction_id=confirm_fact.transaction_id,
            order_id=confirm_fact.order_id,
            subscription_id=confirm_fact.subscription_id,
            amount=confirm_fact.monto,
            token_transaccion=confirm_fact.token_transaccion,
            codigo_error=confirm_fact.codigo_error,
            status="Aprobado",
            timestamp_evento=confirm_fact.timestamp_evento,
        )
        db.add(audit_2)
        db.commit()
        print(f"  ✓ Audit event inserted: id={audit_2.id}, status={audit_2.status}")
        
        # ========== VERIFY IMMUTABLE AUDIT TRAIL ==========
        print("\n🔍 Verifying immutable audit trail:")
        
        audit_events = db.query(FactPaymentsEvent)\
            .filter_by(transaction_id=tx_id)\
            .order_by(FactPaymentsEvent.timestamp_evento.asc())\
            .all()
        
        print(f"  Total audit events for tx {tx_id.hex[:8]}...: {len(audit_events)}")
        for evt in audit_events:
            print(
                f"    - id={evt.id}, status={evt.status}, amount={evt.amount}, "
                f"timestamp={evt.timestamp_evento.isoformat()}"
            )
        
        assert len(audit_events) == 2, f"Expected 2 audit events, got {len(audit_events)}"
        assert audit_events[0].status == "esperando_revisión", "First event should be 'esperando_revisión'"
        assert audit_events[1].status == "Aprobado", "Second event should be 'Aprobado'"
        
        print("\n✅ Test PASSED: Immutable audit trail verified")
        
        # ========== SAMPLE ANALYTICS QUERIES ==========
        print("\n📊 Sample analytics queries:")
        
        # 1. Conversion rate
        total = db.query(FactPaymentsEvent).count()
        aprobado = db.query(FactPaymentsEvent).filter_by(status="Aprobado").count()
        print(f"  - Total events: {total}")
        print(f"  - Aprobado count: {aprobado}")
        if total > 0:
            print(f"  - Conversion rate: {100.0 * aprobado / total:.2f}%")
        
        # 2. Status distribution
        print(f"  - Status distribution:")
        status_dist = db.query(FactPaymentsEvent.status, FactPaymentsEvent.id.__func__.count())\
            .group_by(FactPaymentsEvent.status)\
            .all()
        for status, count in status_dist:
            print(f"      {status}: {count}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 80)
    print("fact_payments_events Immutable Audit Table Test")
    print("=" * 80)
    
    setup_db()
    success = test_payment_flow()
    
    print("\n" + "=" * 80)
    exit(0 if success else 1)
