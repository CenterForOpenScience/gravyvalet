from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
)

from addon_service.authorized_account.views import AuthorizedAccountViewSet

from .models import AuthorizedLinkAccount
from .serializers import AuthorizedLinkAccountSerializer


@extend_schema_view(
    create=extend_schema(
        description='Create new authorized link account for given external link service.\n For OAuth services it\'s required to create account with `"initiate_oauth"=true` in order to proceed with OAuth flow'
    ),
)
class AuthorizedLinkAccountViewSet(AuthorizedAccountViewSet):
    queryset = AuthorizedLinkAccount.objects.all()
    serializer_class = AuthorizedLinkAccountSerializer
