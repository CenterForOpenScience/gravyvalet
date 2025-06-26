from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)

from addon_imps.storage.google_drive import GoogleDriveStorageImp
from addon_service.authorized_account.views import AuthorizedAccountViewSet

from .models import AuthorizedStorageAccount
from .serializers import (
    AuthorizedStorageAccountSerializer,
    GoogleDriveStorageAccountSerializer,
)


@extend_schema_view(
    create=extend_schema(
        description='Create new authorized storage account for given external storage service.\n For OAuth services it\'s required to create account with `"initiate_oauth"=true` in order to proceed with OAuth flow'
    ),
)
class AuthorizedStorageAccountViewSet(AuthorizedAccountViewSet):
    queryset = AuthorizedStorageAccount.objects.all()
    serializer_class = AuthorizedStorageAccountSerializer

    def get_serializer(self, *args, **kwargs):
        kwargs["context"] = self.get_serializer_context()
        if self.action == "partial_update":
            authorized_account = self.get_object()
            if (
                authorized_account.external_service.addon_imp.imp_cls
                == GoogleDriveStorageImp
            ):
                return GoogleDriveStorageAccountSerializer(*args, **kwargs)
        return self.serializer_class(*args, **kwargs)
