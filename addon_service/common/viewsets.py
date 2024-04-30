import dataclasses

from rest_framework import mixins as drf_mixins
from rest_framework.exceptions import (
    NotFound,
    PermissionDenied,
)
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


class _DrfJsonApiHelpers(AutoPrefetchMixin, PreloadIncludesMixin, RelatedMixin):
    pass


class RestrictedReadOnlyViewSet(ReadOnlyModelViewSet):
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
        self.filter_backends = [RestrictedListEndpointFilterBackend]

        qs = self.filter_queryset(self.get_queryset())
        try:
            self.check_object_permissions(self.request, qs.get())
        except qs.model.DoesNotExist:
            raise NotFound("Provided filter returned no results.")
        except qs.model.MultipleObjectsReturned:
            raise PermissionDenied(
                "Filters to this endpoint must be uniquely identifying"
            )

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class RetrieveWriteViewSet(
    _DrfJsonApiHelpers,
    drf_mixins.CreateModelMixin,
    drf_mixins.RetrieveModelMixin,
    drf_mixins.UpdateModelMixin,
    GenericViewSet,
):
    http_method_names = ["get", "post", "patch", "head", "options"]


class RetrieveWriteDeleteViewSet(
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
