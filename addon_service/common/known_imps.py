"""Addon implementation registry for the addon service

supports both static built-in addons and dynamically registered addons.
import and add new static implementations here to make them available.
"""

import enum
import logging
from collections.abc import (
    Iterable,
    Iterator,
)

from django.apps import apps

from addon_imps.citations import (
    mendeley,
    zotero_org,
)
from addon_imps.computing import boa
from addon_imps.link import dataverse as link_dataverse
from addon_imps.storage import (
    bitbucket,
    box_dot_com,
    dataverse,
    dropbox,
    figshare,
    github,
    gitlab,
    google_drive,
    onedrive,
    owncloud,
    s3,
)
from addon_toolkit import AddonImp
from addon_toolkit.interfaces.foreign_addon_config import ForeignAddonConfig


logger = logging.getLogger(__name__)

if __debug__:
    from addon_imps.storage import my_blarg

__all__ = ("AddonRegistry",)


class AddonRegistry:
    """
    Registry for addons in use.
    """

    _name_imp_map: dict[str, type[AddonImp]] = {}
    _number_name_map: dict[int, str] = {}

    @classmethod
    def register_addon_apps(cls, addon_apps: dict[str, int]) -> None:
        foreign_addon_imps = {
            ks: cfg.imp
            for cfg in apps.get_app_configs()
            if isinstance(cfg, ForeignAddonConfig)
            for ks in (cfg.addon_name, cfg.name)
        }
        for name, number in addon_apps.items():
            if name in KnownAddonImps.__members__:
                cls.register(name, number, KnownAddonImps[name].value)
            elif name in foreign_addon_imps:
                cls.register(name, number, foreign_addon_imps[name])
            else:
                logger.warning(
                    f"No addon app has name {name}. "
                    "Forgot to add an app to INSTALLED_APPS?"
                )

    @classmethod
    def register(cls, addon_name: str, imp_number: int, imp: AddonImp) -> None:
        if imp_number in cls._number_name_map:
            if (
                addon_name in cls._name_imp_map
                and addon_name == cls._number_name_map.get(imp_number)
            ):
                logger.info(
                    f"Addon {addon_name} has already been registered correctrly."
                )
                return
            else:
                logger.error(
                    f"imp number {imp_number} is specified for 2 addons -- "
                    f"{addon_name} and {cls._number_name_map[imp_number]}"
                )
            raise ValueError("imp number conflict")

        cls._name_imp_map[addon_name] = imp
        cls._number_name_map[imp_number] = addon_name

    @classmethod
    def get_all_addon_imps(cls) -> Iterable[type[AddonImp]]:
        return cls._name_imp_map.values()

    @classmethod
    def iter_by_type(cls, addon_type: type[AddonImp]) -> Iterator[tuple[int, str]]:
        return (
            (number, name)
            for number, name in cls._number_name_map.items()
            if issubclass(cls._name_imp_map[name], addon_type)
        )

    @classmethod
    def get_imp_by_name(cls, imp_name: str) -> type[AddonImp]:
        return cls._name_imp_map[imp_name]

    @classmethod
    def get_imp_name(cls, imp: type[AddonImp]) -> str:
        for name, registered_imp in cls._name_imp_map.items():
            if registered_imp == imp:
                return name
        raise ValueError(f"Unknown addon imp: {imp}")

    @classmethod
    def get_imp_by_number(cls, imp_number: int) -> type[AddonImp]:
        return cls.get_imp_by_name(cls.get_name_by_number(imp_number))

    @classmethod
    def get_imp_number(cls, imp: type[AddonImp]) -> int:
        imp_name = cls.get_imp_name(imp)
        for number, name in cls._number_name_map.items():
            if name == imp_name:
                return number
        raise ValueError(f"Unknown addon imp : {imp}")

    @classmethod
    def get_name_by_number(cls, imp_number: int) -> str:
        return cls._number_name_map[imp_number]

    @classmethod
    def clear(cls) -> None:
        """Clear all registrations."""
        cls._name_imp_map.clear()
        cls._number_name_map.clear()


###
# Static registry of known addon implementations -- add new imps to
# KnownAddonImps below.


@enum.unique
class KnownAddonImps(enum.Enum):
    """Static mapping from API-facing name for an AddonImp to the Imp itself.

    Note: Grouped by type and then ordered by respective imp numbers assigned
    in apps.settings.
    """

    # Type: Storage
    BOX = box_dot_com.BoxDotComStorageImp
    S3 = s3.S3StorageImp
    GOOGLEDRIVE = google_drive.GoogleDriveStorageImp
    DROPBOX = dropbox.DropboxStorageImp
    FIGSHARE = figshare.FigshareStorageImp
    ONEDRIVE = onedrive.OneDriveStorageImp
    OWNCLOUD = owncloud.OwnCloudStorageImp
    DATAVERSE = dataverse.DataverseStorageImp
    GITLAB = gitlab.GitlabStorageImp
    BITBUCKET = bitbucket.BitbucketStorageImp
    GITHUB = github.GitHubStorageImp

    # Type: Citation
    ZOTERO = zotero_org.ZoteroOrgCitationImp
    MENDELEY = mendeley.MendeleyCitationImp

    # Type: Cloud Computing
    BOA = boa.BoaComputingImp

    # Type: Link
    LINK_DATAVERSE = link_dataverse.DataverseLinkImp

    if __debug__:
        BLARG = my_blarg.MyBlargStorage
