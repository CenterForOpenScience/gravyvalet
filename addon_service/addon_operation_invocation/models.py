import traceback

import jsonschema
from django.core.exceptions import ValidationError
from django.db import models

from addon_service.common.base_model import AddonsServiceBaseModel
from addon_service.common.invocation_status import InvocationStatus
from addon_service.common.validators import validate_invocation_status
from addon_service.models import AddonOperationModel


class AddonOperationInvocation(AddonsServiceBaseModel):
    int_invocation_status = models.IntegerField(
        validators=[validate_invocation_status],
        default=InvocationStatus.STARTING.value,
    )
    operation_identifier = models.TextField()  # TODO: validator
    operation_kwargs = models.JSONField(default=dict, blank=True)
    thru_addon = models.ForeignKey(
        "ConfiguredStorageAddon", null=True, blank=True, on_delete=models.CASCADE
    )
    thru_account = models.ForeignKey(
        "AuthorizedStorageAccount", on_delete=models.CASCADE
    )
    by_user = models.ForeignKey("UserReference", on_delete=models.CASCADE)
    operation_result = models.JSONField(null=True, default=None, blank=True)
    exception_type = models.TextField(blank=True, default="")
    exception_message = models.TextField(blank=True, default="")
    exception_context = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["operation_identifier"]),
            models.Index(fields=["exception_type"]),
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
        return AddonOperationModel.get_by_static_key(self.operation_identifier)

    @operation.setter
    def operation(self, value: AddonOperationModel):
        self.operation_identifier = value.static_key

    @property
    def operation_name(self) -> str:
        return self.operation.name

    @property
    def owner_uri(self) -> str:
        return self.by_user.user_uri

    def clean_fields(self, *args, **kwargs):
        super().clean_fields(*args, **kwargs)
        try:
            jsonschema.validate(
                instance=self.operation_kwargs,
                schema=self.operation.params_jsonschema,
            )
        except jsonschema.exceptions.ValidationError as _exception:
            raise ValidationError(_exception)
        if self.thru_addon is not None and (
            self.thru_addon.base_account_id != self.thru_account_id
        ):
            raise ValidationError(
                {"thru_addon": "thru_addon and thru_account must agree"}
            )

    def set_exception(self, exception: BaseException) -> None:
        self.invocation_status = InvocationStatus.EXCEPTION
        self.exception_type = type(exception).__qualname__
        self.exception_message = repr(exception)
        _tb = traceback.TracebackException.from_exception(exception)
        self.exception_context = "\n".join(_tb.format(chain=True))

    def clear_exception(self) -> None:
        self.exception_type = ""
        self.exception_message = ""
        self.exception_context = ""
