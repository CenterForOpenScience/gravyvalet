import dataclasses


@dataclasses.dataclass(frozen=True, kw_only=True)
class AccessTokenCredentials:
    access_token: str


@dataclasses.dataclass(frozen=True, kw_only=True)
class AccessKeySecretKeyCredentials:
    access_key: str
    secret_key: str


@dataclasses.dataclass(frozen=True, kw_only=True)
class UsernamePasswordCredentials:
    username: str
    password: str
