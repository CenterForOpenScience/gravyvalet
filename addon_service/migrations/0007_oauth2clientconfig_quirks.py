# Generated by Django 4.2.7 on 2024-11-27 12:05

from django.db import (
    migrations,
    models,
)


class Migration(migrations.Migration):

    dependencies = [
        (
            "addon_service",
            "0006_externalcitationservice_int_supported_features_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="oauth2clientconfig",
            name="quirks",
            field=models.IntegerField(
                blank=True,
                choices=[(1, "Only Access Token"), (2, "Non Expirable Refresh Token")],
                null=True,
            ),
        ),
    ]
