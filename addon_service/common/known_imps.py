"""the single static source of truth for addon implementations known to the addon service

import and add new implementations here to make them available in the api
"""

import enum

from addon_imps.citations import (
    mendeley,
    zotero_org,
)
from addon_imps.computing import boa
from addon_imps.link import dataverse as link_dataverse, zenodo
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
    """Static mapping from API-facing name for an AddonImp to the Imp itself.

    Note: Grouped by type and then ordered by respective AddonImpNumbers.
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
    ZENODO = zenodo.ZenodoLinkImp

    if __debug__:
        BLARG = my_blarg.MyBlargStorage


@enum_names_same_as(KnownAddonImps)
@enum.unique
class AddonImpNumbers(enum.Enum):
    """Static mapping from each AddonImp name to a unique integer (for database use)

    Note: Ideally, we should "prefix" the number by type and take future scalability into account.
    e.g. Storage type uses 10xx, Citation type uses 11xx, Cloud Computing type uses 12xx and LINK type uses 13xx.
    Consider this a future improvement when we run out of 1001~1019 for both storage and citation addons.
    """

    # Type: Storage
    BOX = 1001
    S3 = 1003
    GOOGLEDRIVE = 1005
    DROPBOX = 1006
    FIGSHARE = 1007
    ONEDRIVE = 1008
    OWNCLOUD = 1009
    DATAVERSE = 1010
    GITLAB = 1011
    BITBUCKET = 1012
    GITHUB = 1013

    # Type: Citation
    ZOTERO = 1002
    MENDELEY = 1004

    # Type: Cloud Computing
    BOA = 1020

    # Type: Link
    LINK_DATAVERSE = 1030
    ZENODO = 1031

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
