import dataclasses
import datetime
from typing import Optional


class CredentialsBase:
    def validate(self):
        return True


@dataclasses.dataclass(kw_only=True)
class OAuth2Credentials(CredentialsBase):
    access_token: Optional[str] = None
    state_token: Optional[str] = None
    refresh_token: Optional[str] = None
    access_token_expiration: Optional[datetime.datetime] = None
    authorized_scopes: list

    def validate(self):
        if bool(self.access_token) == bool(self.state_token):
            raise ValueError(
                "OAuth2 credentials must specify exactly one of `state_token` or `access token`"
            )

        if self.access_token and not self.refresh_token:
            raise ValueError(
                "OAuth2 credentials with an active access token must also specify "
                "a refresh token to enable renewing authorization."
            )


@dataclasses.dataclass(kw_only=True)
class PersonalAccessTokenCredentials(CredentialsBase):
    access_token: str


@dataclasses.dataclass(kw_only=True)
class AccessKeySecretKeyCredentials(CredentialsBase):
    access_key: str
    secret_key: str


@dataclasses.dataclass(kw_only=True)
class UsernamePasswordCredentials(CredentialsBase):
    username: str
    password: str
