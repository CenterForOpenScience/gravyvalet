import dataclasses
import typing

from rest_framework import mixins as drf_mixins
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.viewsets import (
    GenericViewSet,
    ViewSet,
)
from rest_framework_json_api.views import (
    AutoPrefetchMixin,
    PreloadIncludesMixin,
    ReadOnlyModelViewSet,
    RelatedMixin,
)

from .filtering import RestrictedListEndpointFilterBackend
from .static_dataclass_model import StaticDataclassModel


class _DrfJsonApiHelpers(AutoPrefetchMixin, PreloadIncludesMixin, RelatedMixin):
    pass


class RestrictedReadOnlyViewSet(ReadOnlyModelViewSet):
    filter_backends = [RestrictedListEndpointFilterBackend]
    """ReadOnlyViewSet that requires `list` actions return only one result.

    UserReference and ResourceReference endpoints are major entry points into
    our system, but callers have no a priori way of knowing internal ids for these
    endpoints. We also do not want to inappropriately leak user information
    by allowing unrestricted access to `list` operations on these endpoints.

    As such, this viewset implements a restricted version of `list` endpoints
    that allows subclasses to define required filters that *must* be used to
    limit the output to a single entry.

    Functionally, this allows requests like
    `v1/user-references/?filter[user_uri]={uri}`
    to act as an alternative to
    `v1/user-references/{pk}`
    in the case where the caller only has the publicly avaialable uri as a key
    """

    def list(self, request, *args, **kwargs):
        """Custom implementation of `list` that uses
        RestrictedListEndpointFilterBackend and check_object_permissions
        to enforce permissions on returned entities.
        """
        qs = self.filter_queryset(self.get_queryset())
        try:
            self.check_object_permissions(self.request, qs.get())
        except qs.model.DoesNotExist:
            return Response([])
        except qs.model.MultipleObjectsReturned:
            raise PermissionDenied(
                "Filters to this endpoint must be uniquely identifying"
            )

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class _CreateWithPermissionsMixin(drf_mixins.CreateModelMixin):
    def perform_create(self, serializer):
        super().perform_create(serializer)
        _instance = serializer.instance
        # check permissions on the created instance (which may or may not be saved)
        self.check_object_permissions(self.request, _instance)
        if serializer.instance._state.adding:
            # the serializer didn't save it
            _instance.save()


class RetrieveCreateViewSet(
    _DrfJsonApiHelpers,
    _CreateWithPermissionsMixin,
    drf_mixins.RetrieveModelMixin,
    GenericViewSet,
):
    """viewset allowing create, retrieve, update"""

    http_method_names = ["get", "post", "head", "options"]


class RetrieveWriteViewSet(
    _DrfJsonApiHelpers,
    _CreateWithPermissionsMixin,
    drf_mixins.RetrieveModelMixin,
    drf_mixins.UpdateModelMixin,
    GenericViewSet,
):
    """viewset allowing create, retrieve, update"""

    http_method_names = ["get", "post", "patch", "head", "options"]


class RetrieveWriteDeleteViewSet(
    _DrfJsonApiHelpers,
    _CreateWithPermissionsMixin,
    drf_mixins.RetrieveModelMixin,
    drf_mixins.UpdateModelMixin,
    drf_mixins.DestroyModelMixin,
    GenericViewSet,
):
    """viewset allowing create, retrieve, update, delete"""

    http_method_names = ["get", "post", "patch", "delete", "head", "options"]


class StaticDataclassViewset(ViewSet, RelatedMixin):
    """viewset for read-only access to any `StaticDataclassModel`"""

    http_method_names = ["get", "head", "options"]
    authentication_classes = ()  # as public as the code they're generated from

    # subclasses must have a `serializer_class` that has
    # a dataclass at `serializer_class.Meta.model`
    serializer_class: typing.Any

    @property
    def dataclass_model(self) -> type[StaticDataclassModel]:
        _model = self.serializer_class.Meta.model
        assert dataclasses.is_dataclass(_model) and issubclass(
            _model, StaticDataclassModel
        )
        return _model

    def retrieve(self, request, pk):
        _obj = self.dataclass_model.get_by_pk(pk)
        _serializer = self.get_serializer_class()(
            _obj, context=self.get_serializer_context()
        )
        return Response(_serializer.data)

    def list(self, request):
        _obj_list = list(self.dataclass_model.iter_all())
        _serializer = self.get_serializer_class()(
            _obj_list,
            context=self.get_serializer_context(),
            many=True,
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
