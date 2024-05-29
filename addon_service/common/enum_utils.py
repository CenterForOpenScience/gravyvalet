import enum
import operator
from functools import reduce


def combine_flags(member_list):
    return reduce(operator.__or__, member_list)


def enum_names(some_enum: type[enum.Enum]) -> set[str]:
    return set(some_enum.__members__.keys())
