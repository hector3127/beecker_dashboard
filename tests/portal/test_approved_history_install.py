"""Carga inicial sin archivos externos y protección de históricos locales."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.datastore.models import (
    DmKpiMetric,
    DmKpiPeriod,
    FacturabilityClose,
    SheetSnapshot,
)
from apps.datastore.services.approved_history import install_approved_history
from apps.portal.services.capacity_reference import REFERENCE_SHEET


class ApprovedHistoryTests(TestCase):
    def test_command_installs_and_is_idempotent(self):
        call_command("sync_datastore", pasos="historicos", stdout=StringIO())
        self.assertEqual(FacturabilityClose.objects.count(), 21)
        self.assertEqual(DmKpiPeriod.objects.count(), 10)
        self.assertTrue(DmKpiMetric.objects.exists())
        self.assertEqual(
            len(SheetSnapshot.objects.get(name=REFERENCE_SHEET).rows), 856
        )
        self.assertEqual(
            install_approved_history(),
            {
                "facturability": 0,
                "kpi_dm": 0,
                "capacity": 0,
            },
        )

    def test_existing_months_are_not_replaced(self):
        install_approved_history()
        close = FacturabilityClose.objects.filter(view="general").first()
        close.metrics = {"reviewed": True}
        close.save()
        period = DmKpiPeriod.objects.first()
        period.status = "pending"
        period.save()
        snapshot = SheetSnapshot.objects.get(name=REFERENCE_SHEET)
        snapshot.rows[1][3] = 123.45
        snapshot.save()
        install_approved_history()
        close.refresh_from_db()
        period.refresh_from_db()
        snapshot.refresh_from_db()
        self.assertEqual(close.metrics, {"reviewed": True})
        self.assertEqual(period.status, "pending")
        self.assertEqual(snapshot.rows[1][3], 123.45)
