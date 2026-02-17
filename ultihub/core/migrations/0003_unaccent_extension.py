from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0002_create_default_appsettings"),
    ]

    operations = [
        UnaccentExtension(),
    ]
