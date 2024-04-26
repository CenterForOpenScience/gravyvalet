class AddonServiceException(Exception):
    pass


class ExpiredAccessToken(AddonServiceException):
    pass
