import enum


class ServiceTypes(enum.Flag):
    """to what extent can a service be configured with a user's custom url"""

    PUBLIC = enum.auto()
    """`ServiceTypes.PUBLIC`: the service exists at a specific public domain

    (`api_base_url` must be set on the service and may _not_ be set on the account)
    """
    HOSTED = enum.auto()
    """`ServiceTypes.HOSTED`: the service must be self-hosted

    (`api_base_url` is not set on the service and _must_ be set on the account)
    """
    HYBRID = PUBLIC | HOSTED
    """`ServiceTypes.HYBRID`: the service exists at a specific public domain but may also be self-hosted

    (`api_base_url` should be set on the service but may be overridden on the account)
    """
