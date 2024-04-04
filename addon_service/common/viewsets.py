import dataclasses

from rest_framework import mixins as drf_mixins
from rest_framework.response import Response
from rest_framework.viewsets import (
    GenericViewSet,
    ViewSet,
)
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


class DataclassViewset(ViewSet, RelatedMixin):
    http_method_names = ["get", "head", "options"]

    # set in subclasses:
    serializer_class: type  # should have a dataclass at serializer_class.Meta.model

    def retrieve(self, request, pk):
        _obj = self.dataclass_model.get_by_pk(pk)
        _serializer = self.get_serializer_class()(
            _obj, context=self.get_serializer_context()
        )
        return Response(_serializer.data)

    # for RelatedMixin
    def get_object(self):
        return self.dataclass_model.get_by_pk(self.kwargs["pk"])

    # for RelatedMixin
    def get_serializer_class(self):
        return self.serializer_class

    # for RelatedMixin
    def get_serializer_context(self):
        return {"request": self.request}

    @property
    def dataclass_model(self):
        _model = self.serializer_class.Meta.model  # type: ignore
        assert dataclasses.is_dataclass(_model) and isinstance(_model, type)
        return _model
