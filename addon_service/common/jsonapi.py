import dataclasses
import re
from typing import (
    ClassVar,
    Iterable,
    Pattern,
)


@dataclasses.dataclass(frozen=True)
class JSONAPIQueryParam:
    """Dataclass for describing the contents of a JSON:API-compliant Query Parameter."""

    family: str
    members: tuple[str] = ()  # Term "member" borrowed from jsonapi.net
    values: tuple[str] = ()

    # Matches any alphanumeric string followed by an open bracket or end of input
    # (can include "_" or "-" if outside of the first or last position)
    # Note: [^\W_] is equivalent to [a-zA-Z0-9]
    FAMILY_REGEX: ClassVar[Pattern] = re.compile(r"^[^\W_]([\w-]*[^\W^])?(?=\[|$)")
    # Captures any text located within square brackets
    MEMBER_REGEX: ClassVar[Pattern] = re.compile(r"\[(?P<name>[^[\]]*)\]")

    @classmethod
    def from_key_value_pair(
        cls, query_param_name: str, query_param_values: Iterable[str]
    ) -> "JSONAPIQueryParam":
        family, members = cls.parse_param_name(query_param_name)
        if not isinstance(query_param_values, tuple):
            query_param_values = tuple(query_param_values)
        return cls(family, members, query_param_values)

    @classmethod
    def parse_param_name(cls, query_param_name: str) -> tuple[str, tuple[str]]:
        """Parses a query parameter name into its family and bracketed members.

        >>> JSONAPIQueryParam.parse_param_name('filter')
        ('filter', ())

        >>> JSONAPIQueryParam.parse_param_name('filter[field]')
        ('filter', ('field',))

        >>> JSONAPIQueryParam.parse_param_name('filter[nested][field]')
        ('filter', ('nested', 'field'))
        """
        if not cls._param_name_is_valid(query_param_name):
            raise ValueError(f"Invalid query param name: {query_param_name}")
        family = cls.FAMILY_REGEX.match(query_param_name).group()
        members = cls.MEMBER_REGEX.findall(query_param_name)
        return (family, tuple(members))

    @classmethod
    def _param_name_is_valid(cls, query_param_name: str) -> bool:
        """Validates that a given query parameter has a valid name in JSON:API.

        >>> JSONAPIQueryParam._param_name_is_valid('filter')
        True

        >>> JSONAPIQueryParam._param_name_is_valid('filter[so][many][nested][fields]')
        True

        >>> JSONAPIQueryParam._param_name_is_valid('_filter')
        False

        >>> JSONAPIQueryParam._param_name_is_valid('fi&lter')
        False

        >>> JSONAPIQueryParam._param_name_is_valid('filter[field')
        False

        >>> JSONAPIQueryParam._param_name_is_valid('filter[field]extra')
        False
        """
        # Full match is FAMILY followed by 0 or more MEMBERS followed by end of input
        full_match_regex = re.compile(
            f"{cls.FAMILY_REGEX.pattern}({cls.MEMBER_REGEX.pattern})*$"
        )
        if not full_match_regex.match(query_param_name):
            return False
        return True

    def __str__(self):
        bracketed_members = "".join([f"[{member}]" for member in self.members])
        values = ",".join([str(value) for value in self.values])
        return f"{self.family}{bracketed_members}={values}"


QueryParamFamilies = dict[str, Iterable[JSONAPIQueryParam]]


def group_query_params_by_family(
    query_items: Iterable[tuple[str, Iterable[str]]]
) -> QueryParamFamilies:
    """Extracts JSON:API query familes from a list of (ParameterName, ParameterValues) tuples.

    Data should be pre-normalized before calling, such as by using the results of
    `urllib.parse.parse_qs(...).items()` or `django.utils.QueryDict.lists()`
    """
    grouped_query_params = QueryParamFamilies()
    for _unparsed_name, _param_values in query_items:
        parsed_query_param = JSONAPIQueryParam.from_key_value_pair(
            _unparsed_name, _param_values
        )
        grouped_query_params.setdefault(parsed_query_param.family, []).append(
            parsed_query_param
        )
    return grouped_query_params
