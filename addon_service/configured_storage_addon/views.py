from rest_framework_json_api.views import ModelViewSet

from .models import ConfiguredStorageAddon
from .serializers import (
    ConfiguredStorageAddonPOSTSerializer,
    ConfiguredStorageAddonSerializer,
)


class ConfiguredStorageAddonViewSet(ModelViewSet):
    queryset = ConfiguredStorageAddon.objects.all()
    serializer_class = ConfiguredStorageAddonSerializer

    def get_serializer(self, *args, **kwargs):
        if self.request.method == "POST":
            return ConfiguredStorageAddonPOSTSerializer(
                data=self.request.data, context={"request": self.request}
            )
        else:
            return super().get_serializer(*args, **kwargs)
