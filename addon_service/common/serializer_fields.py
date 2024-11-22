import dataclasses

from rest_framework import serializers as drf_serializers
from rest_framework_json_api import serializers as json_api_serializers
from rest_framework_json_api.relations import (
    PolymorphicResourceRelatedField,
    ResourceRelatedField,
    SkipDataMixin,
)


class ReadOnlyResourceRelatedField(
    json_api_serializers.ResourceRelatedField, drf_serializers.ReadOnlyField
):
    """read-only version of `rest_framework_json_api.serializers.ResourceRelatedField`"""

    pass


class DataclassRelatedLinkField(SkipDataMixin, ResourceRelatedField):
    """related field for use with to-many `StaticDataclassModel` relations"""

    def __init__(self, /, dataclass_model, read_only=True, **kwargs):
        assert dataclasses.is_dataclass(dataclass_model)
        return super().__init__(
            read_only=read_only,
            model=dataclass_model,
            **kwargs,
        )


class DataclassRelatedDataField(ResourceRelatedField):
    """related field for use with to-one `StaticDataclassModel` relations"""

    def __init__(self, /, dataclass_model, **kwargs):
        assert dataclasses.is_dataclass(dataclass_model)
        return super().__init__(
            model=dataclass_model,
            **kwargs,
        )

    def get_queryset(self):
        return _FakeQuerysetForDataclassModel(self.model)


class _FakeQuerysetForDataclassModel:
    def __init__(self, dataclass_model):
        self.model = dataclass_model

    def get(self, *, pk):
        return self.model.get_by_pk(pk)


class CustomPolymorphicResourceRelatedField(PolymorphicResourceRelatedField):
    def to_representation(self, value):
        data = super().to_representation(value)
        if hasattr(value, "authorizedcitationaccount"):
            data["type"] = "authorized-citation-account"
        elif hasattr(value, "authorizedstorageaccount"):
            data["type"] = "authorized-storage-account"
        elif hasattr(value, "configuredstorageaddon"):
            data["type"] = "configured-storage-addon"
        elif hasattr(value, "configuredstorageaccount"):
            data["type"] = "configured-storage-account"
        else:
            raise ValueError("unknown polymorphic type")
        return data
