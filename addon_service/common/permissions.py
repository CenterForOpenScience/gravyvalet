from rest_framework import (
    exceptions,
    permissions,
)

from addon_service.models import UserReference
from app.authentication import authenticate_resource


def fetch_session_user_uri(func):
    """
    Decorator to fetch 'user_reference_uri' from the session and pass it to the permission check function.
    """

    def wrapper(self, request, view, obj=None):
        session_user_uri = request.session.get("user_reference_uri")
        if not session_user_uri:
            raise exceptions.NotAuthenticated("User is not authenticated.")
        if obj:
            return func(self, request, view, obj, session_user_uri)
        return func(self, request, view, session_user_uri)

    return wrapper


class SessionUserIsAccountOwner(permissions.BasePermission):
    @fetch_session_user_uri
    def has_object_permission(self, request, view, obj, user_uri):
        return user_uri == obj.account_owner.user_uri


class SessionUserIsUserReference(permissions.BasePermission):
    @fetch_session_user_uri
    def has_object_permission(self, request, view, obj, user_uri):
        return user_uri == obj.user_uri


class SessionUserIsCSAOwner(permissions.BasePermission):
    @fetch_session_user_uri
    def has_object_permission(self, request, view, obj, user_uri):
        return user_uri == obj.base_account.external_account.owner.user_uri


class SessionUserIsResourceReferenceOwner(permissions.BasePermission):
    @fetch_session_user_uri
    def has_object_permission(self, request, view, obj, user_uri):
        resource_uri = authenticate_resource(request, obj.resource_uri, "read")
        return obj.resource_uri == resource_uri


class CanCreateCSA(permissions.BasePermission):
    @fetch_session_user_uri
    def has_permission(self, request, view, user_uri):
        authorized_resource_id = request.data.get("authorized_resource", {}).get("id")
        if authenticate_resource(request, authorized_resource_id, "admin"):
            return True
        return False


class CanCreateASA(permissions.BasePermission):
    @fetch_session_user_uri
    def has_permission(self, request, view, user_uri):
        request_user_uri = request.data.get("account_owner", {}).get("id")
        if not user_uri == request_user_uri:
            raise exceptions.NotAuthenticated(
                "Account owner ID is missing in the request."
            )
        try:
            UserReference.objects.get(user_uri=user_uri)
            return True
        except UserReference.DoesNotExist:
            raise exceptions.NotAuthenticated("User does not exist.")
