import enum


@enum.unique
class AddonCapabilities(enum.Flag):
    """the source of truth for recognized names in the "addon capabilities" namespace

    when you want portability (like an open api), use this enum's member names

    when you want compactness (maybe a database), use this enum's member values
    """

    ACCESS = enum.auto()
    UPDATE = enum.auto()
