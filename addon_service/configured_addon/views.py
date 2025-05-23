from addon_service.common.permissions import (
    IsAuthenticated,
    IsValidHMACSignedRequest,
    SessionUserCanViewReferencedResource,
    SessionUserIsOwnerOrResourceAdmin,
    SessionUserMayConnectAddon,
)
from addon_service.common.viewsets import RetrieveWriteDeleteViewSet


class ConfiguredAddonViewSet(RetrieveWriteDeleteViewSet):
    allowed_query_params = ["view_only"]

    def get_permissions(self):
        match self.action:
            case "retrieve" | "retrieve_related":
                return [SessionUserCanViewReferencedResource()]
            case "partial_update" | "update" | "destroy":
                return [IsAuthenticated(), SessionUserIsOwnerOrResourceAdmin()]
            case "create":
                return [IsAuthenticated(), SessionUserMayConnectAddon()]
            case "get_wb_credentials":
                return [IsValidHMACSignedRequest()]
            case None:
                return super().get_permissions()
            case _:
                raise NotImplementedError(
                    f"no permission implemented for action '{self.action}'"
                )
