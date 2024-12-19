# Generated by Django 5.1.1 on 2024-12-23 09:12

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("clubs", "0008_clubnotification"),
    ]

    operations = [
        migrations.AddField(
            model_name="club",
            name="short_name",
            field=models.CharField(
                blank=True,
                help_text="Short name of the club (2-3 characters)",
                max_length=3,
                validators=[django.core.validators.MinLengthValidator(2)],
            ),
        ),
    ]
