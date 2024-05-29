import enum


class ServiceTypes(enum.Flag):
    PUBLIC = enum.auto()
    HOSTED = enum.auto()
