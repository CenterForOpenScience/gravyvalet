from addon_service.authorized_account.views import AuthorizedAccountViewSet

from .models import AuthorizedComputingAccount
from .serializers import AuthorizedComputingAccountSerializer


class AuthorizedComputingAccountViewSet(AuthorizedAccountViewSet):
    queryset = AuthorizedComputingAccount.objects.all()
    serializer_class = AuthorizedComputingAccountSerializer
