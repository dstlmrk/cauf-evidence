# Generated by Django 5.1.1 on 2024-12-11 09:57

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("competitions", "0005_alter_competitionapplication_invoice"),
    ]

    operations = [
        migrations.AddField(
            model_name="season",
            name="invoices_generated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
