import jsonschema
from django.core.exceptions import ValidationError
from django.db import models

from addon_service.common.base_model import AddonsServiceBaseModel
from addon_service.common.enums.validators import validate_invocation_status
from addon_service.common.invocation import InvocationStatus
from addon_service.models import AddonOperationModel


class AddonOperationInvocation(AddonsServiceBaseModel):
    int_invocation_status = models.IntegerField(
        validators=[validate_invocation_status],
        default=InvocationStatus.STARTING.value,
    )
    operation_identifier = models.TextField()  # TODO: validator
    operation_kwargs = models.JSONField(
        default=dict, blank=True
    )  # TODO: validate in `clean()`
    thru_addon = models.ForeignKey("ConfiguredStorageAddon", on_delete=models.CASCADE)
    by_user = models.ForeignKey("UserReference", on_delete=models.CASCADE)
    operation_result = models.JSONField(null=True, default=None, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["operation_identifier"]),
        ]

    class JSONAPIMeta:
        resource_name = "addon-operation-invocations"

    @property
    def invocation_status(self):
        return InvocationStatus(self.int_invocation_status)

    @invocation_status.setter
    def invocation_status(self, value):
        self.int_invocation_status = InvocationStatus(value).value

    @property
    def operation(self) -> AddonOperationModel:
        return AddonOperationModel.get_by_natural_key_str(self.operation_identifier)

    @property
    def owner_uri(self) -> str:
        return self.by_user.user_uri

    def clean(self):
        try:
            jsonschema.validate(
                instance=self.operation_kwargs,
                schema=self.operation.params_jsonschema,
            )
        except jsonschema.exceptions.ValidationError as _error:
            raise ValidationError(_error)
