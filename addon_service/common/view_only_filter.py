from rest_framework.filters import BaseFilterBackend


class ViewOnlyFilter(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if "view_only" in request.query_params:
            pass
        return queryset
