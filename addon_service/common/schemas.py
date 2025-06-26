from rest_framework.decorators import action
from rest_framework_json_api.relations import ResourceRelatedField


def auto_related_actions(cls):
    """
    A class decorator that automatically adds a DRF @action for each
    relationship on a ViewSet's serializer_class.
    """
    # Find the serializer
    serializer_class = getattr(cls, "serializer_class", None)
    if not serializer_class:
        return cls

    # Find all relationship fields
    relationship_fields = {
        field_name: field
        for field_name, field in serializer_class().get_fields().items()
        if isinstance(field, ResourceRelatedField)
    }

    for field_name, field in relationship_fields.items():
        # This is the handler that will be used for our action.
        # It's a bridge to the existing `retrieve_related` method.
        def related_field_handler(self, request, *args, **kwargs):
            # We pass the field_name explicitly to retrieve_related
            kwargs["related_field"] = field_name
            return self.retrieve_related(request, *args, **kwargs)

        # Set docstrings for better schema descriptions
        related_field_handler.__doc__ = (
            f"Retrieve the related {field_name} for this resource."
        )
        related_field_handler.__name__ = f"{field_name}_related_action"

        # Decorate our handler with @action. This is what the router looks for.
        # The `url_path` will be the same as the field name.
        decorated_handler = action(
            detail=True,
            methods=["get"],
            url_path=field_name,
        )(related_field_handler)

        # Attach the brand new, decorated method to the ViewSet class
        setattr(cls, f"{field_name}_related_action", decorated_handler)

    return cls
