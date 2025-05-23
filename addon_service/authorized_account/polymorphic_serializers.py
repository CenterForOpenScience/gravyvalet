from rest_framework_json_api import serializers

from addon_service.authorized_account.citation.serializers import (
    AuthorizedCitationAccountSerializer,
)
from addon_service.authorized_account.computing.serializers import (
    AuthorizedComputingAccountSerializer,
)
from addon_service.authorized_account.link.serializers import (
    AuthorizedLinkAccountSerializer,
)
from addon_service.authorized_account.models import AuthorizedAccount
from addon_service.authorized_account.storage.serializers import (
    AuthorizedStorageAccountSerializer,
)


class AuthorizedAccountPolymorphicSerializer(serializers.PolymorphicModelSerializer):
    polymorphic_serializers = [
        AuthorizedCitationAccountSerializer,
        AuthorizedComputingAccountSerializer,
        AuthorizedStorageAccountSerializer,
        AuthorizedLinkAccountSerializer,
    ]

    class Meta:
        model = AuthorizedAccount
