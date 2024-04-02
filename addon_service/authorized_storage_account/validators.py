from django.core.exceptions import ValidationError

from addon_service.credentials import CredentialsFormats
from addon_service.external_storage_service import ServiceTypes


def validate_api_base_url(account):
    service = account.external_service
    if account._api_base_url and not service.configurable_api_root:
        raise ValidationError(
            {
                "api_base_url": f"Cannot specify an api_base_url for Public-only service {service.name}"
            }
        )
    if ServiceTypes.PUBLIC not in service.service_type and not account.api_base_url:
        raise ValidationError(
            {
                "api_base_url": f"Must specify an api_base_url for Hosted-only service {service.name}"
            }
        )


def validate_oauth_state(account):
    if (
        account.credentials_format is not CredentialsFormats.OAUTH2
        or not account.oauth2_token_metadata
    ):
        return
    if bool(account.credentials) == bool(account.oauth2_token_metadata.state_nonce):
        raise ValidationError(
            {
                "credentials": "OAuth2 accounts must assign exactly one of state_nonce and access_token"
            }
        )
    if account.credentials and not account.oauth2_token_metadata.refresh_token:
        raise ValidationError(
            {
                "credentials": "OAuth2 accounts with an access token must have a refresh token"
            }
        )
