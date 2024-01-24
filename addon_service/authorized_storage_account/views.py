from rest_framework_json_api.views import ModelViewSet

from .models import AuthorizedStorageAccount
from .serializers import (
    AuthorizedStorageAccountPOSTSerializer,
    AuthorizedStorageAccountSerializer,
)


class AuthorizedStorageAccountViewSet(ModelViewSet):
    queryset = AuthorizedStorageAccount.objects.all()
    serializer_class = AuthorizedStorageAccountSerializer
    # TODO: permissions_classes

    def get_serializer(self, *args, **kwargs):
        if self.request.method == "POST":
            return AuthorizedStorageAccountPOSTSerializer(
                data=self.request.data, context={"request": self.request}
            )
        else:
            return super().get_serializer(*args, **kwargs)
