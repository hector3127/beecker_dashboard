"""Retire superseded EVA cuts, preserving all Summary inventory evidence."""

from django.db import migrations


def retire_old_cuts(apps, schema_editor):
    """Remove only the pre-inventory pipeline's observations and lock."""
    extraction_model = apps.get_model("datastore", "EvaExtraction")
    ids = [
        run.pk
        for run in extraction_model.objects.all()
        if run.metrics.get("kind") != "summary_inventory"
    ]
    extraction_model.objects.filter(pk__in=ids).delete()
    apps.get_model("datastore", "SyncLock").objects.filter(
        name="eva_native"
    ).delete()


class Migration(migrations.Migration):
    """Only data from the pipeline explicitly retired by the user."""

    dependencies = [("datastore", "0009_azure_revision_history")]
    operations = [
        migrations.RunPython(retire_old_cuts, migrations.RunPython.noop)
    ]
