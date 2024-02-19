from rest_framework import (
    exceptions,
    permissions,
)

from addon_service.models import UserReference
from app.authentication import authenticate_resource


class SessionUserIsOwner(permissions.BasePermission):
    """
    Decorator to fetch 'user_reference_uri' from the session and pass it to the permission check function.
    """

    def has_object_permission(self, request, view, obj):
        session_user_uri = request.session.get("user_reference_uri")
        if session_user_uri:
            assert session_user_uri == obj.owner_reference


class SessionUserIsResourceReferenceOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        resource_uri = authenticate_resource(request, obj.resource_uri, "read")
        return obj.resource_uri == resource_uri


class CanCreateCSA(permissions.BasePermission):
    def has_permission(self, request, view):
        authorized_resource_id = request.data.get("authorized_resource", {}).get("id")
        if authenticate_resource(request, authorized_resource_id, "admin"):
            return True
        return False


class CanCreateASA(permissions.BasePermission):
    def has_permission(self, request, view):
        session_user_uri = request.session.get("user_reference_uri")
        request_user_uri = request.data.get("account_owner", {}).get("id")
        if not session_user_uri == request_user_uri:
            raise exceptions.NotAuthenticated(
                "Account owner ID is missing in the request."
            )
        try:
            UserReference.objects.get(user_uri=request_user_uri)
            return True
        except UserReference.DoesNotExist:
            raise exceptions.NotAuthenticated("User does not exist.")
