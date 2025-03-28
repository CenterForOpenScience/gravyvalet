from addon_service.authorized_account.views import AuthorizedAccountViewSet

from .models import AuthorizedLinkAccount
from .serializers import AuthorizedLinkAccountSerializer


class AuthorizedStorageAccountViewSet(AuthorizedAccountViewSet):
    queryset = AuthorizedLinkAccount.objects.all()
    serializer_class = AuthorizedLinkAccountSerializer
