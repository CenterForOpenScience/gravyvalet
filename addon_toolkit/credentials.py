import dataclasses
import datetime
from typing import Optional


class CredentialsBase:
    def validate(self):
        return True


@dataclasses.dataclass
class OAuth2Credentials(CredentialsBase):
    access_token: Optional[str] = None
    state_token: Optional[str] = None
    refresh_token: Optional[str] = None
    access_token_expiration: Optional[datetime.datetime] = None
    authorized_scopes: list

    def validate(self):
        if not (self.access_token or self.state_token):
            raise ValueError(
                "OAuth2 credentials without an active access token must specify "
                "a state token to identify the active authorization flow"
            )

        if self.access_token and not self.refresh_token:
            raise ValueError(
                "OAuth2 credentials with an active access token must also specify "
                "a refresh token to enable renewing authorization."
            )


@dataclasses.dataclass
class PersonalAccessTokenCredentials(CredentialsBase):
    access_token: str


@dataclasses.dataclass
class AccessKeySecretKeyCredentials(CredentialsBase):
    access_key: str
    secret_key: str


@dataclasses.dataclass
class UsernamePasswordCredentials(CredentialsBase):
    username: str
    password: str
