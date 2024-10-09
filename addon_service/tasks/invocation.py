import celery
from django.db import transaction

from addon_service.addon_imp.instantiation import get_addon_instance__blocking
from addon_service.common.dibs import dibs
from addon_service.common.invocation_status import InvocationStatus
from addon_service.models import AddonOperationInvocation
from addon_toolkit.json_arguments import json_for_typed_value


__all__ = (
    "perform_invocation__blocking",
    "perform_invocation__celery",
)


def perform_invocation__blocking(invocation: AddonOperationInvocation) -> None:
    """perform the given invocation: run an operation thru an addon and handle any errors"""
    # implemented as a sync function for django transactions
    with dibs(invocation):  # TODO: handle dibs errors
        try:
            _imp = get_addon_instance__blocking(
                invocation.imp_cls,  # type: ignore[arg-type]  #(TODO: generic impstantiation)
                invocation.thru_account,
                invocation.config,
            )
            _operation = invocation.operation
            # inner transaction to contain database errors,
            # so status can be saved in the outer transaction (from `dibs`)
            with transaction.atomic():
                _result = _imp.invoke_operation__blocking(
                    _operation.declaration,
                    invocation.operation_kwargs,
                )
            invocation.operation_result = json_for_typed_value(
                _operation.declaration.result_dataclass,
                _result,
            )
            invocation.invocation_status = InvocationStatus.SUCCESS
        except BaseException as _e:
            invocation.set_exception(_e)
            raise  # TODO: or swallow?
        finally:
            invocation.save()


@celery.shared_task(acks_late=True)
def perform_invocation__celery(invocation_pk: str) -> None:
    perform_invocation__blocking(AddonOperationInvocation.objects.get(pk=invocation_pk))
