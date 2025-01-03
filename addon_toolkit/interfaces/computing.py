"""a static (and still in progress) definition of what composes a computing addon"""

import dataclasses
import typing

from addon_toolkit.constrained_network.http import HttpRequestor
from addon_toolkit.credentials import Credentials
from addon_toolkit.imp import AddonImp

from ._base import BaseAddonInterface


__all__ = (
    "ComputingAddonInterface",
    "ComputingAddonImp",
    "ComputingConfig",
)


###
# dataclasses used for operation args and return values


@dataclasses.dataclass(frozen=True)
class ComputingConfig:
    external_api_url: str
    external_account_id: str | None = None


###
# declaration of all computing addon operations


class ComputingAddonInterface(BaseAddonInterface, typing.Protocol):

    pass


@dataclasses.dataclass
class ComputingAddonImp(AddonImp):
    """base class for computing addon implementations"""

    ADDON_INTERFACE = ComputingAddonInterface

    config: ComputingConfig

    async def build_wb_config(self) -> dict:
        return {}


@dataclasses.dataclass
class ComputingAddonHttpRequestorImp(ComputingAddonImp):
    """base class for computing addon implementations using GV network"""

    network: HttpRequestor


@dataclasses.dataclass
class ComputingAddonClientRequestorImp[T](ComputingAddonImp):
    """base class for computing addon with custom clients"""

    client: T = dataclasses.field(init=False)
    credentials: dataclasses.InitVar[Credentials]

    def __post_init__(self, credentials):
        self.client = self.create_client(credentials)

    @staticmethod
    def create_client(credentials) -> T:
        raise NotImplementedError
