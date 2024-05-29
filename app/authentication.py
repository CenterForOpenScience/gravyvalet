from rest_framework import authentication as drf_authentication
from rest_framework.request import Request as DrfRequest

from addon_service.common import osf


class GVCombinedAuthentication(drf_authentication.BaseAuthentication):
    """Authentication supporting session, basic, and token methods."""

    def authenticate(self, request: DrfRequest):
        _user_uri = osf.get_osf_user_uri(request._request)
        if _user_uri:
            request.session["user_reference_uri"] = _user_uri
            return (True, None)  # TODO load UserReference?
        return None  # unauthenticated

    def authenticate_header(self, request):
        """Specify the value for the WWW-Authenticate header in a 401 response.

        see https://www.rfc-editor.org/rfc/rfc9110#name-www-authenticate
        """
        return True  # TODO?
