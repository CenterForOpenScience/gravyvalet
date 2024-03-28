# Generated by Django 4.2.7 on 2024-03-28 04:09

import django.contrib.postgres.fields
from django.db import (
    migrations,
    models,
)


class Migration(migrations.Migration):
    dependencies = [
        ("addon_service", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="authorizedstorageaccount",
            name="authorized_scopes",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(), blank=True, null=True, size=None
            ),
        ),
        migrations.AddField(
            model_name="externalcredentials",
            name="state_token",
            field=models.CharField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="externalstorageservice",
            name="callback_url",
            field=models.URLField(default=""),
        ),
        migrations.AddField(
            model_name="externalstorageservice",
            name="default_scopes",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(), blank=True, null=True, size=None
            ),
        ),
    ]
