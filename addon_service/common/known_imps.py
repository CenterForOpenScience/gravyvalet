"""the single static source of truth for addon implementations known to the addon service

import and add new implementations here to make them available in the api
"""

import enum

from addon_imps.citations import (
    mendeley,
    zotero_org,
)
from addon_imps.storage import (
    box_dot_com,
    dataverse,
    figshare,
    google_drive,
    s3,
)
from addon_service.common.enum_decorators import enum_names_same_as
from addon_toolkit import AddonImp


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

    BOX_DOT_COM = box_dot_com.BoxDotComStorageImp
    S3 = s3.S3StorageImp
    ZOTERO_ORG = zotero_org.ZoteroOrgCitationImp
    GOOGLE_DRIVE = google_drive.GoogleDriveStorageImp
    FIGSHARE = figshare.FigshareStorageImp
    MENDELEY = mendeley.MendeleyCitationImp
    DATAVERSE = dataverse.DataverseStorageImp

    if __debug__:
        BLARG = my_blarg.MyBlargStorage


@enum.unique
@enum_names_same_as(KnownAddonImps)
class AddonImpNumbers(enum.Enum):
    """Static mapping from each AddonImp name to a unique integer (for database use)"""

    BOX_DOT_COM = 1001
    ZOTERO_ORG = 1002
    S3 = 1003
    MENDELEY = 1004
    GOOGLE_DRIVE = 1005
    FIGSHARE = 1007
    DATAVERSE = 1008

    if __debug__:
        BLARG = -7
