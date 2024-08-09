from addon_service.abstract.authorized_account.views import AuthorizedAccountViewSet

from .models import AuthorizedCitationAccount
from .serializers import AuthorizedCitationAccountSerializer


class AuthorizedCitationAccountViewSet(AuthorizedAccountViewSet):
    queryset = AuthorizedCitationAccount.objects.all()
    serializer_class = AuthorizedCitationAccountSerializer
