import dataclasses
import typing


@dataclasses.dataclass(frozen=True, kw_only=True)
class Credentials(typing.Protocol):
    """abstract base for dataclasses representing common shapes of credentials"""

    def iter_headers(self) -> typing.Iterator[tuple[str, str]]:
        yield from ()


@dataclasses.dataclass(frozen=True, kw_only=True)
class AccessTokenCredentials(Credentials):
    access_token: str

    def iter_headers(self):
        yield "Authorization", f"Bearer {self.access_token}"


@dataclasses.dataclass(frozen=True, kw_only=True)
class AccessKeySecretKeyCredentials(Credentials):
    access_key: str
    secret_key: str


@dataclasses.dataclass(frozen=True, slots=True)
class OAuth1Credentials(Credentials):
    oauth_token: str
    oauth_token_secret: str

    def iter_headers(self) -> typing.Iterator[tuple[str, str]]:
        """
        This is Zotero specific as other OAuth1.0a clients require request signing,
        as per current architecture, we cannot it here.
        """

        yield "Authorization", f"Bearer {self.oauth_token_secret}"
        # TODO: implement request signing for OAuth1.0a services that require it

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
