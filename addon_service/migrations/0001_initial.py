# Generated by Django 4.2.7 on 2024-03-28 18:40

import django.contrib.postgres.fields
import django.db.models.deletion
from django.db import (
    migrations,
    models,
)

import addon_service.common.enums.validators


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="AuthorizedStorageAccount",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(editable=False)),
                ("modified", models.DateTimeField()),
                (
                    "int_authorized_capabilities",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.IntegerField(
                            validators=[
                                addon_service.common.enums.validators.validate_addon_capability
                            ]
                        ),
                        size=None,
                    ),
                ),
                (
                    "authorized_scopes",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(), blank=True, null=True, size=None
                    ),
                ),
                ("default_root_folder", models.CharField(blank=True)),
            ],
            options={
                "verbose_name": "Authorized Storage Account",
                "verbose_name_plural": "Authorized Storage Accounts",
            },
        ),
        migrations.CreateModel(
            name="CredentialsIssuer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(editable=False)),
                ("modified", models.DateTimeField()),
                ("name", models.CharField()),
            ],
            options={
                "verbose_name": "External Service",
                "verbose_name_plural": "External Services",
            },
        ),
        migrations.CreateModel(
            name="ExternalCredentials",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(editable=False)),
                ("modified", models.DateTimeField()),
                ("oauth_key", models.CharField(blank=True, null=True)),
                ("oauth_secret", models.CharField(blank=True, null=True)),
                ("refresh_token", models.CharField(blank=True, null=True)),
                ("date_last_refreshed", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("state_token", models.CharField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "External Credentials",
                "verbose_name_plural": "External Credentials",
            },
        ),
        migrations.CreateModel(
            name="ResourceReference",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(editable=False)),
                ("modified", models.DateTimeField()),
                ("resource_uri", models.URLField(db_index=True, unique=True)),
            ],
            options={
                "verbose_name": "Resource Reference",
                "verbose_name_plural": "Resource References",
            },
        ),
        migrations.CreateModel(
            name="UserReference",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(editable=False)),
                ("modified", models.DateTimeField()),
                ("user_uri", models.URLField(db_index=True, unique=True)),
                ("deactivated", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "User Reference",
                "verbose_name_plural": "User References",
            },
        ),
        migrations.CreateModel(
            name="ExternalStorageService",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(editable=False)),
                ("modified", models.DateTimeField()),
                (
                    "int_addon_imp",
                    models.IntegerField(
                        validators=[
                            addon_service.common.enums.validators.validate_storage_imp_number
                        ]
                    ),
                ),
                (
                    "default_scopes",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(), blank=True, null=True, size=None
                    ),
                ),
                ("max_concurrent_downloads", models.IntegerField()),
                ("max_upload_mb", models.IntegerField()),
                ("auth_uri", models.URLField()),
                ("callback_url", models.URLField(default="")),
                ("api_base_url", models.URLField()),
                (
                    "credentials_issuer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="external_storage_services",
                        to="addon_service.credentialsissuer",
                    ),
                ),
            ],
            options={
                "verbose_name": "External Storage Service",
                "verbose_name_plural": "External Storage Services",
            },
        ),
        migrations.CreateModel(
            name="ExternalAccount",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(editable=False)),
                ("modified", models.DateTimeField()),
                (
                    "credentials",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="external_accounts",
                        to="addon_service.externalcredentials",
                    ),
                ),
                (
                    "credentials_issuer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="external_accounts",
                        to="addon_service.credentialsissuer",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="external_accounts",
                        to="addon_service.userreference",
                    ),
                ),
            ],
            options={
                "verbose_name": "External Account",
                "verbose_name_plural": "External Accounts",
            },
        ),
        migrations.CreateModel(
            name="ConfiguredStorageAddon",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(editable=False)),
                ("modified", models.DateTimeField()),
                ("root_folder", models.CharField(blank=True)),
                (
                    "int_connected_capabilities",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.IntegerField(
                            validators=[
                                addon_service.common.enums.validators.validate_addon_capability
                            ]
                        ),
                        size=None,
                    ),
                ),
                (
                    "authorized_resource",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="configured_storage_addons",
                        to="addon_service.resourcereference",
                    ),
                ),
                (
                    "base_account",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="configured_storage_addons",
                        to="addon_service.authorizedstorageaccount",
                    ),
                ),
            ],
            options={
                "verbose_name": "Configured Storage Addon",
                "verbose_name_plural": "Configured Storage Addons",
            },
        ),
        migrations.AddField(
            model_name="authorizedstorageaccount",
            name="external_account",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="authorized_storage_accounts",
                to="addon_service.externalaccount",
            ),
        ),
        migrations.AddField(
            model_name="authorizedstorageaccount",
            name="external_storage_service",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="authorized_storage_accounts",
                to="addon_service.externalstorageservice",
            ),
        ),
        migrations.CreateModel(
            name="AddonOperationInvocation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created", models.DateTimeField(editable=False)),
                ("modified", models.DateTimeField()),
                (
                    "int_invocation_status",
                    models.IntegerField(
                        default=1,
                        validators=[
                            addon_service.common.enums.validators.validate_invocation_status
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
                    "thru_addon",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="addon_service.configuredstorageaddon",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["operation_identifier"],
                        name="addon_servi_operati_4bdf63_idx",
                    ),
                    models.Index(
                        fields=["exception_type"], name="addon_servi_excepti_35dee4_idx"
                    ),
                ],
            },
        ),
    ]
