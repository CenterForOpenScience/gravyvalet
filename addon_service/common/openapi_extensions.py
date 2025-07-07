from drf_spectacular.extensions import OpenApiFilterExtension


class RestrictedReadOnlyViewSetExtension(OpenApiFilterExtension):
    target_class = "addon_service.common.filtering.RestrictedListEndpointFilterBackend"  # full dotted path

    def get_schema_operation_parameters(self, auto_schema, *args, **kwargs):
        if auto_schema.method != "GET" or "list" not in auto_schema.view.action:
            return []

        required_filter_fields = getattr(
            auto_schema.view, "required_list_filter_fields", ()
        )

        parameters = []
        for field_name in required_filter_fields:
            parameters.append(
                {
                    "name": f"filter[{field_name}]",
                    "in": "query",  # This corresponds to OpenApiParameter.QUERY
                    "description": f"Filter by {field_name}. This filter must be uniquely identifying.",
                    "required": True,
                    "schema": {
                        "type": "string"  # This corresponds to OpenApiTypes.STR, OpenApiTypes.URI, etc.
                    },
                }
            )
        return parameters
