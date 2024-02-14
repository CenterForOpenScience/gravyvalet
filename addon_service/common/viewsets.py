from rest_framework import mixins as drf_mixins
from rest_framework.viewsets import GenericViewSet
from rest_framework_json_api.views import (
    AutoPrefetchMixin,
    PreloadIncludesMixin,
    RelatedMixin,
)


class _DrfJsonApiHelpers(AutoPrefetchMixin, PreloadIncludesMixin, RelatedMixin):
    pass


class RetrieveOnlyViewSet(
    _DrfJsonApiHelpers, drf_mixins.RetrieveModelMixin, GenericViewSet
):
    http_method_names = ["get", "head", "options"]


class RetrieveWriteViewSet(
    _DrfJsonApiHelpers,
    drf_mixins.CreateModelMixin,
    drf_mixins.RetrieveModelMixin,
    drf_mixins.UpdateModelMixin,
    drf_mixins.DestroyModelMixin,
    GenericViewSet,
):
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
