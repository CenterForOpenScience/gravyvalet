from rest_framework_json_api.views import ModelViewSet

from .models import ConfiguredStorageAddon
from .serializers import ConfiguredStorageAddonSerializer


class ConfiguredStorageAddonViewSet(ModelViewSet):
    queryset = ConfiguredStorageAddon.objects.all()
    serializer_class = ConfiguredStorageAddonSerializer
