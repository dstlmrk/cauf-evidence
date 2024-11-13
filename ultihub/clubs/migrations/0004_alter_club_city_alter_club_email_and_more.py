# Generated by Django 5.1.1 on 2024-11-13 20:58

from django.db import migrations, models

import clubs.validators


class Migration(migrations.Migration):
    dependencies = [
        ("clubs", "0003_club_identification_number_club_organization_name_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="club",
            name="city",
            field=models.CharField(
                blank=True, help_text="City where the club is located", max_length=64
            ),
        ),
        migrations.AlterField(
            model_name="club",
            name="email",
            field=models.EmailField(
                blank=True, help_text="Contact email of the club", max_length=254
            ),
        ),
        migrations.AlterField(
            model_name="club",
            name="identification_number",
            field=models.CharField(
                blank=True,
                help_text="Company identification number",
                max_length=8,
                validators=[clubs.validators.validate_identification_number],
            ),
        ),
        migrations.AlterField(
            model_name="club",
            name="organization_name",
            field=models.CharField(
                blank=True,
                help_text="Name of the organization with legal entity status",
                max_length=64,
            ),
        ),
        migrations.AlterField(
            model_name="club",
            name="website",
            field=models.URLField(blank=True, help_text="URL of the club's website"),
        ),
    ]
