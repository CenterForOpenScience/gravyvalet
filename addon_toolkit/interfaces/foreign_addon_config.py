from abc import (
    ABC,
    abstractmethod,
)

from django.apps import AppConfig

from ..imp import AddonImp


class ForeignAddonConfig(AppConfig, ABC):
    """Abstract Base Class for Foreign addons"""

    @property
    @abstractmethod
    def imp(self) -> AddonImp:
        """Return the AddonImp subclass of this Foreign Addon."""
        pass

    @property
    @abstractmethod
    def addon_name(self) -> str:
        """
        Return the unique name identifying this addon app on the gravyvalet
        system.
        """
        pass
