import enum


class InvocationStatus(enum.Enum):
    """coarse-grained status of an addon operation invocation"""

    STARTING = 1
    """the invocation has been recorded and enqueued"""
    GOING = 2
    """work on the invocation has begun"""
    SUCCESS = 3
    """the invocation has succeeded and has a result"""
    ERROR = 128
    """an error occurred"""
