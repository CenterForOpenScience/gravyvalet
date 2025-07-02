from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)

from addon_service.authorized_account.views import AuthorizedAccountViewSet

from .models import AuthorizedComputingAccount
from .serializers import AuthorizedComputingAccountSerializer


@extend_schema_view(
    create=extend_schema(
        description="Create new authorized computing account for given external computing service.\n "
        'For OAuth services it\'s required to create account with `"initiate_oauth"=true` '
        "in order to proceed with OAuth flow"
    ),
)
class AuthorizedComputingAccountViewSet(AuthorizedAccountViewSet):
    queryset = AuthorizedComputingAccount.objects.all()
    serializer_class = AuthorizedComputingAccountSerializer
