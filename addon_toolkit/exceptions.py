"""exception classes for addon_toolkit"""


class AddonToolkitException(Exception):
    """base class for addon_toolkit exceptions"""


###
# imp problems


class NotAnImp(AddonToolkitException):
    """expected an AddonImp, but this is not"""


class ImpHasNoInterface(AddonToolkitException):
    """missing required ADDON_INTERFACE class attribute"""


###
# operation problems


class NotAnOperation(AddonToolkitException):
    """not an operation"""


class OperationNotValid(AddonToolkitException):
    """invalid operation declaration"""


class OperationNotImplemented(AddonToolkitException):
    """operation is declared but not implemented (this may be fine)"""


###
# auto-json problems


class JsonArgumentsError(AddonToolkitException):
    """base exception for addon_toolkit.json_arguments"""


class TypeNotJsonable(JsonArgumentsError):
    """tried using a type annotation that is not easily json-able"""


class ValueNotJsonableWithType(JsonArgumentsError):
    """got a python value mismatched with the expected type annotation"""


class InvalidJsonArgsForSignature(JsonArgumentsError):
    """tried using json kwargs with a mismatched call signature"""


class JsonValueInvalidForType(JsonArgumentsError):
    """got a json value mismatched with a given python type annotation"""
