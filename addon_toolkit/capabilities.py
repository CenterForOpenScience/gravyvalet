import enum


@enum.unique
class AddonCapabilities(enum.Flag):
    """
    each addon operation belongs to one of the capabilities defined here,
    used for coarse-grained permissions that may be delegated to collaborators.

    when you want portability (like an open api), use this enum's member names
    >>> AddonCapabilities.ACCESS.name
    'ACCESS'

    when you want compactness (maybe a database), use this enum's member values
    >>> AddonCapabilities.ACCESS.value
    1
    """

    ACCESS = enum.auto()
    UPDATE = enum.auto()
