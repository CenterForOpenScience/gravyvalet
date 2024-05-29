import addon_service.common.filtering
import addon_service.common.jsonapi
from addon_toolkit.tests._doctest import load_doctests


# for some reason this variable name matters
load_tests = load_doctests(addon_service.common.filtering, addon_service.common.jsonapi)
