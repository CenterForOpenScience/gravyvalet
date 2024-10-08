# Generated by Django 4.2.7 on 2024-09-10 13:51

import django.db.models.deletion
from django.db import (
    migrations,
    models,
)

import addon_service.common.str_uuid_field
import addon_service.common.validators


class Migration(migrations.Migration):

    dependencies = [
        ("addon_service", "0002_externalstorageservice_int_supported_features"),
    ]

    operations = [
        migrations.AddField(
            model_name="configuredcitationaddon",
            name="root_folder",
            field=models.CharField(blank=True),
        ),
        migrations.CreateModel(
            name="CitationOperationInvocation",
            fields=[
                (
                    "id",
                    addon_service.common.str_uuid_field.StrUUIDField(
                        default=addon_service.common.str_uuid_field.str_uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created", models.DateTimeField(editable=False)),
                ("modified", models.DateTimeField()),
                (
                    "int_invocation_status",
                    models.IntegerField(
                        default=1,
                        validators=[
                            addon_service.common.validators.validate_invocation_status
                        ],
                    ),
                ),
                ("operation_identifier", models.TextField()),
                ("operation_kwargs", models.JSONField(blank=True, default=dict)),
                (
                    "operation_result",
                    models.JSONField(blank=True, default=None, null=True),
                ),
                ("exception_type", models.TextField(blank=True, default="")),
                ("exception_message", models.TextField(blank=True, default="")),
                ("exception_context", models.TextField(blank=True, default="")),
                (
                    "by_user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="addon_service.userreference",
                    ),
                ),
                (
                    "thru_account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="addon_service.authorizedcitationaccount",
                    ),
                ),
                (
                    "thru_addon",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="addon_service.configuredcitationaddon",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["operation_identifier"],
                        name="addon_servi_operati_33d776_idx",
                    ),
                    models.Index(
                        fields=["exception_type"], name="addon_servi_excepti_2c54c2_idx"
                    ),
                ],
            },
        ),
    ]
