# Generated by Django 4.2.7 on 2025-03-04 14:32

import django.db.models.deletion
from django.db import (
    migrations,
    models,
)


class Migration(migrations.Migration):

    dependencies = [
        ("addon_service", "0011_oauth2tokenmetadata_date_last_refreshed"),
    ]

    operations = [
        migrations.AlterField(
            model_name="authorizedaccount",
            name="_credentials",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="authorized_account",
                to="addon_service.externalcredentials",
            ),
        ),
    ]
