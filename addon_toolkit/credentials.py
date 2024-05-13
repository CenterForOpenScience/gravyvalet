import dataclasses
import typing


@dataclasses.dataclass(frozen=True)
class Credentials(typing.Protocol):
    def asdict(self) -> dict[str, typing.Any]:
        return dataclasses.asdict(self)

    def iter_headers(self) -> typing.Iterator[tuple[str, str]]:
        yield from ()  # no headers unless implemented by subclass


@dataclasses.dataclass(frozen=True, kw_only=True)
class AccessTokenCredentials(Credentials):
    access_token: str

    def iter_headers(self) -> typing.Iterator[tuple[str, str]]:
        yield ("Authorization", f"Bearer {self.access_token}")


@dataclasses.dataclass(frozen=True, kw_only=True)
class AccessKeySecretKeyCredentials(Credentials):
    access_key: str
    secret_key: str


@dataclasses.dataclass(frozen=True, kw_only=True)
class UsernamePasswordCredentials(Credentials):
    username: str
    password: str
