from rest_framework_json_api.filters import QueryParameterValidationFilter


class AllowedQueryParamsFilter(QueryParameterValidationFilter):
    """
    JSONAPI supports specific kind of query params.
    See https://jsonapi.org/format/#query-parameters or check the base class
    But in some cases we need simple query params like "uris", "title", etc.
    Basically the purpose of this filter is to bypass JSONAPI query params validation
    for "allowed_query_params" query params but leave it for others.
    Note: "allowed_query_params" must be set for all viewsets that are used in request
    """

    def filter_queryset(self, request, queryset, view):
        query_params_to_remove = {}
        # our custom query params just should be listed in allowed_query_params
        if hasattr(view, "allowed_query_params"):
            for query_param, value in request.query_params.items():
                if query_param in view.allowed_query_params:
                    query_params_to_remove[query_param] = value

        # remove correct query params from request because they'll fail JSONAPI validation
        request.query_params._mutable = True
        for allowed_query_param in query_params_to_remove:
            request.query_params.pop(allowed_query_param)

        # request.query_params contains query params that aren't listed in allowed_query_params.
        # So it's either incorrect parameter or JSONAPI query parameter
        self.validate_query_params(request)
        # return correct query params for usage in other places
        request.query_params.update(query_params_to_remove)
        request.query_params._mutable = False
        return queryset
