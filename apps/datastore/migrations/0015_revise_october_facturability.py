"""Publish the revised October 2026 close from the reference dashboard."""

from datetime import date

from django.db import migrations

MONTH = date(2026, 10, 1)
SOURCE = (
    "Dashboard de referencia · revisión de Clockify y Bandas/rol del 12/11/2026"
)

GENERAL = {
    "month": "2026-10",
    "label": "Octubre",
    "short_label": "Oct",
    "person_hours": 176.0,
    "capacity": 6456.0,
    "fixed_hours": 4673.4,
    "fixed_percent": 72.39,
    "fixed_hc": 27,
    "variable_capacity": 1782.6000000000004,
    "variable_hours": 1279.1,
    "variable_percent": 71.75,
    "variable_hc": 7,
    "service_hours": [514.75, 166.56666666666666, 0.0, 514.7833333333333],
    "free_hours": 503.50000000000045,
    "free_fte": 3,
    "global_percent": 92.2,
    "bar_height": 0,
    "error": "",
    "other_hours": 83.0,
    "resources": 38,
    "notice": "",
}
SPECIALTIES = [
    {
        "name": "Dev",
        "headcount": 25,
        "capacity": 4176.0,
        "fixed_hours": 3485.0,
        "fixed_percent": 83.45,
        "variable_hours": 528.0833333333334,
        "variable_percent": 76.42,
        "free_fte": 1,
        "fixed_hc": 20,
        "variable_hc": 3,
    },
    {
        "name": "Arq",
        "headcount": 4,
        "capacity": 704.0,
        "fixed_hours": 454.5,
        "fixed_percent": 64.56,
        "variable_hours": 163.75,
        "variable_percent": 65.63,
        "free_fte": 0,
        "fixed_hc": 3,
        "variable_hc": 1,
    },
    {
        "name": "QA",
        "headcount": 4,
        "capacity": 696.0,
        "fixed_hours": 386.0,
        "fixed_percent": 55.46,
        "variable_hours": 203.5,
        "variable_percent": 65.65,
        "free_fte": 1,
        "fixed_hc": 2,
        "variable_hc": 1,
    },
    {
        "name": "BA",
        "headcount": 3,
        "capacity": 528.0,
        "fixed_hours": 179.5,
        "fixed_percent": 34.0,
        "variable_hours": 266.0,
        "variable_percent": 76.33,
        "free_fte": 0,
        "fixed_hc": 1,
        "variable_hc": 2,
    },
    {
        "name": "SM",
        "headcount": 2,
        "capacity": 352.0,
        "fixed_hours": 168.4,
        "fixed_percent": 47.84,
        "variable_hours": 117.76666666666667,
        "variable_percent": 64.14,
        "free_fte": 0,
        "fixed_hc": 1,
        "variable_hc": 1,
    },
    {
        "name": "Lab IA",
        "headcount": 0,
        "capacity": 0,
        "fixed_hours": 0,
        "fixed_percent": 0,
        "variable_hours": 0,
        "variable_percent": 0,
        "free_fte": 0,
        "fixed_hc": 0,
        "variable_hc": 0,
    },
]


def publish_october(apps, schema_editor):
    close = apps.get_model("datastore", "FacturabilityClose")
    records = close.objects.using(schema_editor.connection.alias)
    for view, metrics in (("general", GENERAL), ("especialidad", SPECIALTIES)):
        current = (
            records.filter(month=MONTH, view=view).order_by("-revision").first()
        )
        if current is None or current.metrics != metrics:
            records.create(
                month=MONTH,
                view=view,
                metrics=metrics,
                source=SOURCE,
                revision=current.revision + 1 if current else 1,
            )


def remove_october_revision(apps, schema_editor):
    close = apps.get_model("datastore", "FacturabilityClose")
    close.objects.using(schema_editor.connection.alias).filter(
        month=MONTH, source=SOURCE
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("datastore", "0014_facturability_closes")]
    operations = [
        migrations.RunPython(publish_october, remove_october_revision)
    ]
