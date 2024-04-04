import enum


class InvocationStatus(enum.IntEnum):
    STARTING = 1
    GOING = 2
    SUCCESS = 3
    PROBLEM = 128
