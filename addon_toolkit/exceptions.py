"""exception classes for addon_toolkit"""


class AddonToolkitException(Exception):
    pass


###
# imp problems


class NotAnImp(AddonToolkitException):
    pass


class ImpNotValid(AddonToolkitException):
    pass


class ImpTooAbstract(ImpNotValid):
    pass


class ImpHasTooManyJobs(ImpNotValid):
    pass


class ImpHasNoInterface(ImpNotValid):
    pass


###
# operation problems


class NotAnOperation(AddonToolkitException):
    pass


class OperationNotValid(AddonToolkitException):
    pass


class OperationNotImplemented(AddonToolkitException):
    pass


###
# auto-json problems


class JsonArgumentsError(AddonToolkitException):
    pass


class TypeNotJsonable(JsonArgumentsError):
    pass


class ValueNotJsonableWithType(JsonArgumentsError):
    pass


class InvalidJsonArgsForSignature(JsonArgumentsError):
    pass


class JsonValueInvalidForType(JsonArgumentsError):
    pass
