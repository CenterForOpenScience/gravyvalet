from addon_imps.storage.google_drive import GoogleDriveStorageImp
from addon_service.authorized_account.views import AuthorizedAccountViewSet

from .models import AuthorizedStorageAccount
from .serializers import (
    AuthorizedStorageAccountSerializer,
    GoogleDriveStorageAccountSerializer,
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
