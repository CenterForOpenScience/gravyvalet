from abc import (
    ABC,
    abstractmethod,
)

from django.apps import AppConfig

from ..imp import AddonImp


class ForeignAddonImpConfig(AppConfig, ABC):
    """Abstract Base Class for Foreign Addon Imps"""

    @property
    @abstractmethod
    def imp(self) -> AddonImp:
        """Return the AddonImp subclass of this Foreign Addon Imp."""
        pass

    @property
    @abstractmethod
    def addon_imp_name(self) -> str:
        """
        Return the unique name identifying this addon imp app on the
        gravyvalet system.
        """
        pass
