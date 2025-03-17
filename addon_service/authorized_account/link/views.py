from addon_service.authorized_account.views import AuthorizedAccountViewSet

from .models import AuthorizedLinkAccount
from .serializers import AuthorizedLinkAccountSerializer


class AuthorizedLinkAccountViewSet(AuthorizedAccountViewSet):
    queryset = AuthorizedLinkAccount.objects.all()
    serializer_class = AuthorizedLinkAccountSerializer
