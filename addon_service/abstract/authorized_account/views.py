from abc import ABC

from addon_service.common.permissions import (
    IsAuthenticated,
    SessionUserIsOwner,
)
from addon_service.common.viewsets import RetrieveWriteDeleteViewSet


class AuthorizedAccountViewSet(RetrieveWriteDeleteViewSet, ABC):

    def get_permissions(self):
        match self.action:
            case (
                "retrieve"
                | "retrieve_related"
                | "partial_update"
                | "update"
                | "destroy"
            ):
                return [IsAuthenticated(), SessionUserIsOwner()]
            case "create":
                return [IsAuthenticated()]
            case None:
                return super().get_permissions()
            case _:
                raise NotImplementedError(
                    f"no permission implemented for action '{self.action}'"
                )
