from rest_framework_json_api.relations import HyperlinkedRelatedField


class WritableHyperlinkedRelatedField(HyperlinkedRelatedField):
    def to_internal_value(self, external_value):
        breakpoint()
        _result = super().to_internal_value(external_value)
        return _result
