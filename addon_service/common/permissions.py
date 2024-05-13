from datetime import (
    UTC,
    datetime,
    timedelta,
)

from rest_framework import (
    exceptions,
    permissions,
)

from addon_service.common import hmac as hmac_utils
from addon_service.common import osf
from addon_service.models import ResourceReference


class IsAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.session.get("user_reference_uri") is not None


class SessionUserIsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        session_user_uri = request.session.get("user_reference_uri")
        if session_user_uri:
            return session_user_uri == obj.owner_uri
        return False


class SessionUserCanViewReferencedResource(permissions.BasePermission):
    """for object permissions on objects with a `resource_uri` attribute"""

    def has_object_permission(self, request, view, obj):
        return osf.has_osf_permission_on_resource(
            request,
            obj.resource_uri,
            osf.OSFPermission.READ,
        )


class SessionUserIsReferencedResourceAdmin(permissions.BasePermission):
    """
    assumes request data parsed by a serializer with `authorized_resource`
    to-one relationship and/or `authorized_resource_uri` attribute
    """

    def has_permission(self, request, view):
        resource_uri = None
        try:
            resource_uri = ResourceReference.objects.get(
                id=request.data["authorized_resource"]["id"]
            ).resource_uri
        except (ResourceReference.DoesNotExist, KeyError):
            resource_uri = request.data.get("authorized_resource_uri")

        if resource_uri is None:
            raise exceptions.ParseError

        return osf.has_osf_permission_on_resource(
            request,
            resource_uri,
            osf.OSFPermission.ADMIN,
        )


class SessionUserMayAccessInvocation(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        _user_uri = request.session.get("user_reference_uri")
        if _user_uri == obj.by_user.user_uri:
            return True  # invoker
        if _user_uri == obj.thru_addon.owner_uri:
            return True  # addon owner
        # user with "read" access on the connected osf project
        return osf.has_osf_permission_on_resource(
            request,
            obj.thru_addon.authorized_resource.resource_uri,
            osf.OSFPermission.READ,
        )


class SessionUserMayInvokeThruAddon(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        raise NotImplementedError  # TODO: check invoked operation is allowed


class IsValidHMACSignedRequest(permissions.BasePermission):

    REQUEST_EXPIRATION_SECONDS = 110

    def has_permission(self, request, view):
        expiration_time = datetime.now(UTC) - timedelta(
            seconds=self.REQUEST_EXPIRATION_SECONDS
        )
        request_timestamp_str = request.headers.get("X-Authorization-Timestamp")
        if not request_timestamp_str:
            raise exceptions.PermissionDenied(
                "Missing required 'X-Authorization-Timestamp' value"
            )
        try:
            _request_timestamp = datetime.fromisoformat(request_timestamp_str)
        except ValueError:
            raise exceptions.PermissionDenied(
                "Invalid 'X-Authorization-Timestamp' value"
            )
        if _request_timestamp < expiration_time:
            raise exceptions.PermissionDenied("HMAC Signed Request is expired")
        if _request_timestamp > datetime.now(UTC):
            raise exceptions.PermissionDenied(
                "HMAC Signed Request provided a timestamp from the future"
            )

        try:
            hmac_utils.validate_signed_headers(request)
        except ValueError as e:
            raise exceptions.PermissionDenied(e)
        return True
