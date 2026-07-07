"""
Tests para app.analytics.subscription_kpis.

Cubre funciones puras con mock de sesión SQLAlchemy:
  - get_renewal_rate: 0 total → 0.0, cálculo normal
  - get_error_rate: proporcional a billing_success=False
  - get_auto_service_rate: proporcional a auto_service=True
  - get_subscription_stats: estructura completa de retorno
  - get_subscription_summary: integra las tres funciones anteriores
  - get_retention_rate: active_at_period=0 → 0.0, cálculo porcentual
  - get_all_retention_rates: devuelve las tres claves esperadas
"""

import pytest
from unittest.mock import MagicMock, patch, call


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_scalar_db(*scalars):
    """
    Devuelve un mock de db donde cada llamada consecutiva a .scalar() retorna
    el siguiente valor de *scalars. Útil para funciones que hacen N queries.
    """
    db = MagicMock()
    scalar_iter = iter(scalars)

    def _next_scalar():
        try:
            return next(scalar_iter)
        except StopIteration:
            return 0

    db.query.return_value.filter.return_value.scalar.side_effect = _next_scalar
    db.query.return_value.scalar.side_effect = _next_scalar
    return db


def _scalar_db_single(value):
    db = MagicMock()
    db.query.return_value.filter.return_value.scalar.return_value = value
    db.query.return_value.scalar.return_value = value
    db.query.return_value.filter.return_value.filter.return_value.scalar.return_value = value
    return db


# ─── get_renewal_rate ─────────────────────────────────────────────────────────

class TestGetRenewalRate:
    def test_returns_zero_when_no_subscriptions(self):
        from app.analytics.subscription_kpis import get_renewal_rate
        db = MagicMock()
        db.query.return_value.scalar.return_value = 0
        db.query.return_value.filter.return_value.scalar.return_value = 0
        db.query.return_value.filter.return_value.filter.return_value.scalar.return_value = 0
        result = get_renewal_rate(db)
        assert result == 0.0

    def test_calculates_rate_as_decimal(self):
        from app.analytics.subscription_kpis import get_renewal_rate
        db = MagicMock()
        call_count = [0]

        def _scalar():
            call_count[0] += 1
            # 1st call: total=100, 2nd call: renewed=30
            return 100 if call_count[0] % 2 == 1 else 30

        db.query.return_value.scalar.side_effect = _scalar
        db.query.return_value.filter.return_value.scalar.side_effect = _scalar
        db.query.return_value.filter.return_value.filter.return_value.scalar.side_effect = _scalar

        result = get_renewal_rate(db)
        # Debe ser un porcentaje decimal en el rango [0, 1]
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_result_rounded_to_2_decimals(self):
        from app.analytics.subscription_kpis import _round_percentage
        assert _round_percentage(0.33333) == 0.33


# ─── get_error_rate ───────────────────────────────────────────────────────────

class TestGetErrorRate:
    def test_returns_zero_when_no_subscriptions(self):
        from app.analytics.subscription_kpis import get_error_rate
        db = MagicMock()
        db.query.return_value.scalar.return_value = 0
        db.query.return_value.filter.return_value.scalar.return_value = 0
        db.query.return_value.filter.return_value.filter.return_value.scalar.return_value = 0
        result = get_error_rate(db)
        assert result == 0.0

    def test_returns_float(self):
        from app.analytics.subscription_kpis import get_error_rate
        db = MagicMock()
        db.query.return_value.scalar.return_value = 200
        db.query.return_value.filter.return_value.scalar.return_value = 10
        db.query.return_value.filter.return_value.filter.return_value.scalar.return_value = 10
        result = get_error_rate(db)
        assert isinstance(result, float)


# ─── get_auto_service_rate ────────────────────────────────────────────────────

class TestGetAutoServiceRate:
    def test_returns_zero_when_empty(self):
        from app.analytics.subscription_kpis import get_auto_service_rate
        db = MagicMock()
        db.query.return_value.scalar.return_value = 0
        db.query.return_value.filter.return_value.scalar.return_value = 0
        db.query.return_value.filter.return_value.filter.return_value.scalar.return_value = 0
        result = get_auto_service_rate(db)
        assert result == 0.0

    def test_returns_float_between_0_and_1(self):
        from app.analytics.subscription_kpis import get_auto_service_rate
        db = MagicMock()
        db.query.return_value.scalar.return_value = 50
        db.query.return_value.filter.return_value.scalar.return_value = 25
        db.query.return_value.filter.return_value.filter.return_value.scalar.return_value = 25
        result = get_auto_service_rate(db)
        assert 0.0 <= result <= 1.0


# ─── get_subscription_stats ───────────────────────────────────────────────────

class TestGetSubscriptionStats:
    def _build_db_for_stats(self):
        """
        Simula un escenario con:
          total=100, active=70, renewed=30, billing_success=80,
          auto_service=20, new_subs=15, cancellations=5
          + lista de suscripciones para calcular lifetime
        """
        db = MagicMock()

        # Mockear la query de subs para lifetime
        from datetime import date
        mock_subs = [
            (date(2025, 1, 1), date(2026, 1, 1)),   # 365 días
            (date(2025, 6, 1), None),                 # activa
        ]
        db.query.return_value.filter.return_value.all.return_value = mock_subs

        # Mockear todos los scalars con un contador
        values = iter([100, 70, 30, 80, 20, 15, 5])
        def _scalar():
            try:
                return next(values)
            except StopIteration:
                return 0

        db.query.return_value.count.return_value = 100
        db.query.return_value.scalar.return_value = 0
        db.query.return_value.filter.return_value.count.return_value = 70
        db.query.return_value.filter.return_value.scalar.return_value = 30
        db.query.return_value.filter.return_value.filter.return_value.scalar.return_value = 5
        db.query.return_value.filter.return_value.filter.return_value.count.return_value = 20
        return db

    def test_returns_all_required_keys(self):
        from app.analytics.subscription_kpis import get_subscription_stats
        db = self._build_db_for_stats()
        result = get_subscription_stats(db)

        expected_keys = {
            "total", "active", "renewed", "with_billing_success",
            "with_auto_service", "new_subscriptions", "cancellations",
            "net_growth", "churn_rate", "avg_lifetime_months"
        }
        assert expected_keys.issubset(result.keys())

    def test_net_growth_is_difference(self):
        from app.analytics.subscription_kpis import get_subscription_stats
        db = self._build_db_for_stats()
        result = get_subscription_stats(db)
        assert result["net_growth"] == result["new_subscriptions"] - result["cancellations"]

    def test_churn_rate_is_float(self):
        from app.analytics.subscription_kpis import get_subscription_stats
        db = self._build_db_for_stats()
        result = get_subscription_stats(db)
        assert isinstance(result["churn_rate"], float)

    def test_avg_lifetime_months_is_float(self):
        from app.analytics.subscription_kpis import get_subscription_stats
        db = self._build_db_for_stats()
        result = get_subscription_stats(db)
        assert isinstance(result["avg_lifetime_months"], float)


# ─── get_subscription_summary ────────────────────────────────────────────────

class TestGetSubscriptionSummary:
    def test_structure_has_all_keys(self):
        from app.analytics.subscription_kpis import get_subscription_summary
        db = MagicMock()
        db.query.return_value.scalar.return_value = 0
        db.query.return_value.filter.return_value.scalar.return_value = 0
        db.query.return_value.filter.return_value.filter.return_value.scalar.return_value = 0
        db.query.return_value.count.return_value = 0
        db.query.return_value.filter.return_value.count.return_value = 0
        db.query.return_value.filter.return_value.filter.return_value.count.return_value = 0
        db.query.return_value.filter.return_value.all.return_value = []

        result = get_subscription_summary(db)

        assert "renewal_rate" in result
        assert "error_rate" in result
        assert "auto_service_rate" in result
        assert "stats" in result
        assert isinstance(result["stats"], dict)

    def test_all_rates_are_floats(self):
        from app.analytics.subscription_kpis import get_subscription_summary
        db = MagicMock()
        db.query.return_value.scalar.return_value = 0
        db.query.return_value.filter.return_value.scalar.return_value = 0
        db.query.return_value.filter.return_value.filter.return_value.scalar.return_value = 0
        db.query.return_value.count.return_value = 0
        db.query.return_value.filter.return_value.count.return_value = 0
        db.query.return_value.filter.return_value.filter.return_value.count.return_value = 0
        db.query.return_value.filter.return_value.all.return_value = []

        result = get_subscription_summary(db)
        assert isinstance(result["renewal_rate"], float)
        assert isinstance(result["error_rate"], float)
        assert isinstance(result["auto_service_rate"], float)


# ─── get_retention_rate ───────────────────────────────────────────────────────

class TestGetRetentionRate:
    def test_returns_zero_when_no_active_at_period(self):
        from app.analytics.subscription_kpis import get_retention_rate
        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = 0
        db.query.return_value.filter.return_value.filter.return_value.scalar.return_value = 0
        result = get_retention_rate(db, 30)
        assert result == 0.0

    def test_returns_100_when_all_retained(self):
        from app.analytics.subscription_kpis import get_retention_rate
        db = MagicMock()
        call_n = [0]

        def _scalar():
            call_n[0] += 1
            return 100  # active_at_period=100, retained=100

        db.query.return_value.filter.return_value.scalar.side_effect = _scalar
        db.query.return_value.filter.return_value.filter.return_value.scalar.side_effect = _scalar

        result = get_retention_rate(db, 30)
        assert result == 100.0

    def test_result_rounded_to_2_decimals(self):
        from app.analytics.subscription_kpis import get_retention_rate
        db = MagicMock()
        call_n = [0]

        def _scalar():
            call_n[0] += 1
            return 3 if call_n[0] == 1 else 1  # 33.333...%

        db.query.return_value.filter.return_value.scalar.side_effect = _scalar
        db.query.return_value.filter.return_value.filter.return_value.scalar.side_effect = _scalar

        result = get_retention_rate(db, 30)
        # Resultado redondeado a 2 decimales
        assert result == round(result, 2)

    def test_result_is_percentage_0_to_100(self):
        from app.analytics.subscription_kpis import get_retention_rate
        db = MagicMock()
        call_n = [0]

        def _scalar():
            call_n[0] += 1
            return 80 if call_n[0] == 1 else 60

        db.query.return_value.filter.return_value.scalar.side_effect = _scalar
        db.query.return_value.filter.return_value.filter.return_value.scalar.side_effect = _scalar

        result = get_retention_rate(db, 90)
        assert 0.0 <= result <= 100.0


# ─── get_all_retention_rates ─────────────────────────────────────────────────

class TestGetAllRetentionRates:
    def test_returns_three_periods(self):
        from app.analytics.subscription_kpis import get_all_retention_rates
        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = 0
        db.query.return_value.filter.return_value.filter.return_value.scalar.return_value = 0

        result = get_all_retention_rates(db)

        assert "retention_30_days" in result
        assert "retention_90_days" in result
        assert "retention_annual" in result

    def test_all_values_are_floats(self):
        from app.analytics.subscription_kpis import get_all_retention_rates
        db = MagicMock()
        db.query.return_value.filter.return_value.scalar.return_value = 0
        db.query.return_value.filter.return_value.filter.return_value.scalar.return_value = 0

        result = get_all_retention_rates(db)

        assert isinstance(result["retention_30_days"], float)
        assert isinstance(result["retention_90_days"], float)
        assert isinstance(result["retention_annual"], float)


# ─── get_multi_subscription_rate ─────────────────────────────────────────────

class TestGetMultiSubscriptionRate:
    def test_returns_zero_when_no_active_users(self):
        from app.analytics.subscription_kpis import get_multi_subscription_rate
        db = _make_scalar_db(0)
        result = get_multi_subscription_rate(db)
        assert result == 0.0

    def test_calculates_rate_correctly(self):
        from app.analytics.subscription_kpis import get_multi_subscription_rate
        # total_active_users = 100, multi_sub_users = 15
        db = _make_scalar_db(100, 15)
        
        # Mock sub_count column comparison to avoid TypeError
        subquery_mock = db.query.return_value.filter.return_value.group_by.return_value.subquery.return_value
        subquery_mock.c = MagicMock()
        subquery_mock.c.sub_count = MagicMock()
        subquery_mock.c.sub_count.__gt__.return_value = MagicMock()
        
        result = get_multi_subscription_rate(db)
        assert result == 15.0


