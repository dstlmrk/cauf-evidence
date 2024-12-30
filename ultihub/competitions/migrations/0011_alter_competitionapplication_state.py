# Generated by Django 5.1.4 on 2024-12-30 21:25

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("competitions", "0010_alter_competitionapplication_competition_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="competitionapplication",
            name="state",
            field=models.IntegerField(
                choices=[(1, "Awaiting Payment"), (2, "Paid"), (3, "Accepted"), (4, "Declined")],
                default=1,
            ),
        ),
    ]
