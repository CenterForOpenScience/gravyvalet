import dataclasses
import typing


@dataclasses.dataclass(frozen=True, kw_only=True)
class Credentials(typing.Protocol):
    def iter_headers(self) -> typing.Iterator[tuple[str, str]]:
        yield from ()


@dataclasses.dataclass(frozen=True, kw_only=True)
class AccessTokenCredentials(Credentials):
    access_token: str

    def iter_headers(self):
        yield ("Authorization", f"Bearer {self.access_token}")


@dataclasses.dataclass(frozen=True, kw_only=True)
class AccessKeySecretKeyCredentials(Credentials):
    access_key: str
    secret_key: str


@dataclasses.dataclass(frozen=True, kw_only=True)
class UsernamePasswordCredentials(Credentials):
    username: str
    password: str
