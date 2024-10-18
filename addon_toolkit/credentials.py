import dataclasses
import typing


@dataclasses.dataclass(frozen=True, kw_only=True)
class Credentials(typing.Protocol):
    """abstract base for dataclasses representing common shapes of credentials"""


@dataclasses.dataclass(frozen=True, kw_only=True)
class AccessTokenCredentials(Credentials):
    access_token: str


@dataclasses.dataclass(frozen=True, kw_only=True)
class AccessKeySecretKeyCredentials(Credentials):
    access_key: str
    secret_key: str


@dataclasses.dataclass(frozen=True, slots=True)
class OAuth1Credentials(Credentials):
    oauth_token: str
    oauth_token_secret: str

    @classmethod
    def from_dict(cls, payload: dict) -> "tuple[OAuth1Credentials, dict]":
        """
        This method returns credentials constructed dict and dict with other attributes,
        which may contain provider-specific useful info
        """

        return (
            OAuth1Credentials(
                oauth_token=payload.pop("oauth_token"),
                oauth_token_secret=payload.pop("oauth_token_secret"),
            ),
            payload,
        )


@dataclasses.dataclass(frozen=True, kw_only=True)
class UsernamePasswordCredentials(Credentials):
    username: str
    password: str
