from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("portal", "0001_initial")]
    operations = [
        migrations.AddField(model_name="executiveagreement", name="account", field=models.CharField(max_length=150, blank=True)),
        migrations.AddField(model_name="executiveagreement", name="meeting_source", field=models.CharField(max_length=12, choices=[("direction", "Dirección"), ("board", "Consejo")], default="direction")),
        migrations.AddField(model_name="executiveagreement", name="meeting_date", field=models.DateField(null=True, blank=True)),
    ]
