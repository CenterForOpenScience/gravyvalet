from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)

from addon_service.authorized_account.views import AuthorizedAccountViewSet

from .models import AuthorizedCitationAccount
from .serializers import AuthorizedCitationAccountSerializer


@extend_schema_view(
    create=extend_schema(
        description='Create new authorized citation account for given external citation service.\n For OAuth services it\'s required to create account with `"initiate_oauth"=true` in order to proceed with OAuth flow'
    ),
)
class AuthorizedCitationAccountViewSet(AuthorizedAccountViewSet):
    queryset = AuthorizedCitationAccount.objects.all()
    serializer_class = AuthorizedCitationAccountSerializer
