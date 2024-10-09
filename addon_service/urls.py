from django.urls import path
from rest_framework.routers import (
    Route,
    SimpleRouter,
)
from rest_framework_json_api.utils import get_resource_type_from_serializer

from addon_service import views


###
# routing helpers


class _AddonServiceRouter(SimpleRouter):
    def __init__(self):
        super().__init__()
        self.trailing_slash = "/?"  # allow slash or no slash (override value set by SimpleRouter.__init__)

    routes = [
        *SimpleRouter.routes,
        # add route for all relationship "related" links
        # https://django-rest-framework-json-api.readthedocs.io/en/stable/usage.html#related-urls
        Route(
            url=r"^{prefix}/{lookup}/(?P<related_field>[^/]+){trailing_slash}",
            mapping={"get": "retrieve_related"},
            name="{basename}-related",  # agrees with addon_service.common.view_names.related_view
            detail=False,
            initkwargs={"suffix": "Related"},
        ),
        # note: omitting relationship "self" links because we don't expect to need them
        # (our frontend is fine PATCHing a top-level resource to update a relationship)
        # and rest_framework_json_api's RelationshipView exposes all relationships from
        # the model instead of going through the serializer (unlike `retrieve_related`)
    ]


_router = _AddonServiceRouter()


def _register_viewset(viewset):
    # NOTE: assumes each viewset corresponds to a distinct resource_type
    _resource_type = get_resource_type_from_serializer(viewset.serializer_class)
    _router.register(
        prefix=_resource_type,
        viewset=viewset,
        basename=_resource_type,
    )


###
# register viewsets with _router

_register_viewset(views.AuthorizedStorageAccountViewSet)
_register_viewset(views.ConfiguredStorageAddonViewSet)
_register_viewset(views.ExternalStorageServiceViewSet)
_register_viewset(views.AuthorizedCitationAccountViewSet)
_register_viewset(views.ConfiguredCitationAddonViewSet)
_register_viewset(views.ExternalCitationServiceViewSet)
_register_viewset(views.ResourceReferenceViewSet)
_register_viewset(views.AddonOperationInvocationViewSet)
_register_viewset(views.AddonOperationViewSet)
_register_viewset(views.AddonImpViewSet)
_register_viewset(views.UserReferenceViewSet)


###
# the only public part of this module

__all__ = ("urlpatterns",)

urlpatterns = [
    *_router.urls,
    path(r"oauth2/callback/", views.oauth2_callback_view, name="oauth2-callback"),
    path(r"oauth1/callback/", views.oauth1_callback_view, name="oauth1-callback"),
    path(r"status/", views.status, name="status"),
]
