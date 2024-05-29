import dataclasses
from http import HTTPMethod


@dataclasses.dataclass
class RedirectResult:
    url: str
    method: HTTPMethod = HTTPMethod.GET
