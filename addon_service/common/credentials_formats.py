from enum import (
    Enum,
    unique,
)
from typing import Iterator

from addon_toolkit.credentials import (
    AccessKeySecretKeyCredentials,
    AccessTokenCredentials,
    Credentials,
    OAuth1Credentials,
    UsernamePasswordCredentials,
)


@unique
class CredentialsFormats(Enum):
    """all available credentials formats"""

    UNSPECIFIED = 0
    OAUTH2 = 1
    ACCESS_KEY_SECRET_KEY = 2
    USERNAME_PASSWORD = 3
    PERSONAL_ACCESS_TOKEN = 4
    OAUTH1A = 5
    DATAVERSE_API_TOKEN = 6

    @property
    def dataclass(self):
        """get an `addon_toolkit.credentials.Credentials` subclass for this `CredentialsFormat`"""
        match self:
            case CredentialsFormats.OAUTH2:
                return AccessTokenCredentials
            case CredentialsFormats.OAUTH1A:
                return OAuth1Credentials
            case CredentialsFormats.ACCESS_KEY_SECRET_KEY:
                return AccessKeySecretKeyCredentials
            case CredentialsFormats.PERSONAL_ACCESS_TOKEN:
                return AccessTokenCredentials
            case CredentialsFormats.USERNAME_PASSWORD:
                return UsernamePasswordCredentials
            case CredentialsFormats.DATAVERSE_API_TOKEN:
                return AccessTokenCredentials
        raise ValueError(f"No dataclass support for credentials type {self.name}")

    @property
    def is_direct_from_user(self) -> bool:
        """return True if credentials of this format are provided directly by the user

        (or False if credentials established via oauth or similar)
        """
        return self in {
            CredentialsFormats.ACCESS_KEY_SECRET_KEY,
            CredentialsFormats.USERNAME_PASSWORD,
            CredentialsFormats.PERSONAL_ACCESS_TOKEN,
        }

    def iter_headers(self, credentials: Credentials) -> Iterator[tuple[str, str]]:
        match self:
            case CredentialsFormats.OAUTH2 if isinstance(
                credentials, AccessTokenCredentials
            ):
                yield "Authorization", f"Bearer {credentials.access_token}"
            case CredentialsFormats.OAUTH1A if isinstance(
                credentials, OAuth1Credentials
            ):
                yield "Authorization", f"Bearer {credentials.oauth_token_secret}"
            case CredentialsFormats.DATAVERSE_API_TOKEN if isinstance(
                credentials, AccessTokenCredentials
            ):
                yield "X-Dataverse-key", credentials.access_token
