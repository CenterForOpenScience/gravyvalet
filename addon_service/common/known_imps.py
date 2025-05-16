"""the single static source of truth for addon implementations known to the addon service

import and add new implementations here to make them available in the api
"""

import enum

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
from addon_service.common.enum_decorators import enum_names_same_as
from addon_toolkit import AddonImp
from addon_toolkit.interfaces.citation import CitationAddonImp
from addon_toolkit.interfaces.computing import ComputingAddonImp
from addon_toolkit.interfaces.link import LinkAddonImp
from addon_toolkit.interfaces.storage import StorageAddonImp


if __debug__:
    from addon_imps.storage import my_blarg

__all__ = (
    "AddonImpNumbers",
    "KnownAddonImps",
    "get_imp_by_name",
    "get_imp_by_number",
    "get_imp_name",
)


###
# Public interface for accessing concrete AddonImps via their API-facing name or integer ID (and vice-versa)


def get_imp_by_name(imp_name: str) -> type[AddonImp]:
    return KnownAddonImps[imp_name].value


def get_imp_name(imp: type[AddonImp]) -> str:
    return KnownAddonImps(imp).name


def get_imp_by_number(imp_number: int) -> type[AddonImp]:
    _imp_name = AddonImpNumbers(imp_number).name
    return get_imp_by_name(_imp_name)


def get_imp_number(imp: type[AddonImp]) -> int:
    _imp_name = get_imp_name(imp)
    return AddonImpNumbers[_imp_name].value


###
# Static registry of known addon implementations -- add new imps to the enums below


@enum.unique
class KnownAddonImps(enum.Enum):
    """Static mapping from API-facing name for an AddonImp to the Imp itself"""

    BOX = box_dot_com.BoxDotComStorageImp
    S3 = s3.S3StorageImp
    ONEDRIVE = onedrive.OneDriveStorageImp
    ZOTERO = zotero_org.ZoteroOrgCitationImp
    GOOGLEDRIVE = google_drive.GoogleDriveStorageImp
    FIGSHARE = figshare.FigshareStorageImp
    MENDELEY = mendeley.MendeleyCitationImp
    BITBUCKET = bitbucket.BitbucketStorageImp
    DATAVERSE = dataverse.DataverseStorageImp
    OWNCLOUD = owncloud.OwnCloudStorageImp
    LINK_DATAVERSE = link_dataverse.DataverseLinkImp
    GITHUB = github.GitHubStorageImp
    GITLAB = gitlab.GitlabStorageImp
    DROPBOX = dropbox.DropboxStorageImp

    BOA = boa.BoaComputingImp

    if __debug__:
        BLARG = my_blarg.MyBlargStorage


@enum_names_same_as(KnownAddonImps)
@enum.unique
class AddonImpNumbers(enum.Enum):
    """Static mapping from each AddonImp name to a unique integer (for database use)"""

    BOX = 1001
    ZOTERO = 1002
    S3 = 1003
    MENDELEY = 1004
    GOOGLEDRIVE = 1005
    DROPBOX = 1006
    FIGSHARE = 1007
    ONEDRIVE = 1008
    OWNCLOUD = 1009
    DATAVERSE = 1010
    GITLAB = 1011
    BITBUCKET = 1012

    LINK_DATAVERSE = 1030
    GITHUB = 1013

    BOA = 1020

    if __debug__:
        BLARG = -7


def filter_addons_by_type(addon_type):
    return frozenset(
        {
            AddonImpNumbers[item.name]
            for item in KnownAddonImps
            if issubclass(item.value, addon_type)
        }
    )


StorageAddonImpNumbers = filter_addons_by_type(StorageAddonImp)
CitationAddonImpNumbers = filter_addons_by_type(CitationAddonImp)
ComputingAddonImpNumbers = filter_addons_by_type(ComputingAddonImp)
LinkAddonImpNumbers = filter_addons_by_type(LinkAddonImp)
