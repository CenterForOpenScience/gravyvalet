from django.conf import settings
from rest_framework import (
    exceptions,
    permissions,
)

from addon_service.common import hmac as hmac_utils
from addon_service.common import osf


class IsAuthenticated(permissions.BasePermission):
    """allow any logged-in user"""

    def has_permission(self, request, view):
        return request.session.get("user_reference_uri") is not None


class SessionUserIsOwner(permissions.BasePermission):
    """for object permissions on objects with `owner_uri`"""

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


class SessionUserMayConnectAddon(permissions.BasePermission):
    """for object permissions on objects with `owner_uri` and `resource_uri`"""

    def has_object_permission(self, request, view, obj):
        _user_uri = request.session.get("user_reference_uri")
        return (
            # must be account owner
            (_user_uri == obj.owner_uri)
            # and admin of the osf resource
            and osf.has_osf_permission_on_resource(
                request,
                obj.resource_uri,
                osf.OSFPermission.ADMIN,
            )
        )


class SessionUserMayAccessInvocation(permissions.BasePermission):
    """for object permissions on `addon_service.models.AddonOperationInvocation`"""

    def has_object_permission(self, request, view, obj):
        _user_uri = request.session.get("user_reference_uri")
        return bool(
            # must be the invoker:
            (_user_uri == obj.by_user.user_uri)
            # or the account owner:
            or (_user_uri == obj.thru_account.owner_uri)
            # or a user with "read" access on the connected osf project:
            or osf.has_osf_permission_on_resource(
                request,
                obj.thru_addon.authorized_resource.resource_uri,
                osf.OSFPermission.READ,
            )
        )


class SessionUserMayPerformInvocation(permissions.BasePermission):
    """for object permissions on `addon_service.models.AddonOperationInvocation`"""

    def has_object_permission(self, request, view, obj):
        _user_uri = request.session.get("user_reference_uri")
        _thru_addon = obj.thru_addon
        _thru_account = obj.thru_account
        if _thru_addon is None:
            # when invoking thru account, must be the owner
            return _user_uri == _thru_account.owner_uri
        # when invoking thru addon, may be either...
        return bool(
            # the addon owner:
            (_user_uri == _thru_addon.owner_uri)
            # or a user with sufficient on the connected osf project:
            or osf.has_osf_permission_on_resource(
                request,
                _thru_addon.authorized_resource.resource_uri,
                osf.OSFPermission.for_capabilities(obj.operation.capability),
            )
        )


class IsValidHMACSignedRequest(permissions.BasePermission):
    """allow only requests signed with the known osf hmac key"""

    def has_permission(self, request, view):
        try:
            hmac_utils.validate_signed_request(
                request,
                settings.OSF_HMAC_KEY,
                settings.OSF_HMAC_EXPIRATION_SECONDS,
            )
        except (hmac_utils.NotUsingHmac, hmac_utils.RejectedHmac) as e:
            raise exceptions.PermissionDenied(e)
        return True
