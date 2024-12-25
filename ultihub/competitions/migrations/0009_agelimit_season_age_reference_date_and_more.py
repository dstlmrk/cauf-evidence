# Generated by Django 5.1.4 on 2024-12-27 09:51

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


def forwards_func(apps, schema_editor):  # type: ignore
    Season = apps.get_model("competitions", "Season")
    Season.objects.update(min_allowed_age=14, age_reference_date="2025-12-31")


class Migration(migrations.Migration):
    dependencies = [
        ("competitions", "0008_competitionapplication_final_placement"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="AgeRestriction",
            new_name="AgeLimit",
        ),
        migrations.RenameField(
            model_name="competition",
            old_name="age_restriction",
            new_name="age_limit",
        ),
        migrations.AddField(
            model_name="season",
            name="age_reference_date",
            field=models.DateField(
                help_text="Determining date for age calculation (typically 31st December)",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="season",
            name="min_allowed_age",
            field=models.PositiveSmallIntegerField(
                help_text="Members younger than this age are not allowed to participate",
                null=True,
                validators=[django.core.validators.MaxValueValidator(99)],
            ),
        ),
        migrations.AlterField(
            model_name="agelimit",
            name="max",
            field=models.PositiveSmallIntegerField(
                default=99,
                help_text="Maximum age allowed (inclusive)",
                validators=[django.core.validators.MaxValueValidator(99)],
            ),
        ),
        migrations.AlterField(
            model_name="agelimit",
            name="min",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Minimum age allowed (inclusive)",
                validators=[django.core.validators.MaxValueValidator(99)],
            ),
        ),
        migrations.AlterUniqueTogether(
            name="competition",
            unique_together={("name", "season", "type", "division", "age_limit")},
        ),
        migrations.RunPython(forwards_func, reverse_code=migrations.RunPython.noop),
        migrations.AlterField(
            model_name="season",
            name="age_reference_date",
            field=models.DateField(
                help_text="Determining date for age calculation (typically 31st December)"
            ),
        ),
        migrations.AlterField(
            model_name="season",
            name="min_allowed_age",
            field=models.PositiveSmallIntegerField(
                help_text="Members younger than this age are not allowed to participate",
                validators=[django.core.validators.MaxValueValidator(99)],
            ),
        ),
        migrations.RenameField(
            model_name="agelimit",
            old_name="max",
            new_name="m_max",
        ),
        migrations.RenameField(
            model_name="agelimit",
            old_name="min",
            new_name="m_min",
        ),
        migrations.AlterField(
            model_name="agelimit",
            name="m_max",
            field=models.PositiveSmallIntegerField(
                default=99,
                help_text="Maximum age allowed (inclusive) for men",
                validators=[django.core.validators.MaxValueValidator(99)],
                verbose_name="Maximum age for women",
            ),
        ),
        migrations.AlterField(
            model_name="agelimit",
            name="m_min",
            field=models.PositiveSmallIntegerField(
                default=14,
                help_text="Minimum age allowed (inclusive) for men",
                validators=[django.core.validators.MaxValueValidator(99)],
                verbose_name="Minimum age for men",
            ),
        ),
        migrations.AddField(
            model_name="agelimit",
            name="f_max",
            field=models.PositiveSmallIntegerField(
                default=99,
                help_text="Maximum age allowed (inclusive) for women",
                validators=[django.core.validators.MaxValueValidator(99)],
                verbose_name="Maximum age for women",
            ),
        ),
        migrations.AddField(
            model_name="agelimit",
            name="f_min",
            field=models.PositiveSmallIntegerField(
                default=14,
                help_text="Minimum age allowed (inclusive) for women",
                validators=[django.core.validators.MaxValueValidator(99)],
                verbose_name="Minimum age for women",
            ),
        ),
    ]
