from rest_framework_json_api.views import ModelViewSet

from .models import AuthorizedStorageAccount
from .serializers import AuthorizedStorageAccountSerializer


class AuthorizedStorageAccountViewSet(ModelViewSet):
    queryset = AuthorizedStorageAccount.objects.all()
    serializer_class = AuthorizedStorageAccountSerializer
