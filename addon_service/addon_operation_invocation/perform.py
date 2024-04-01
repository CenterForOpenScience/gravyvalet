from asgiref.sync import sync_to_async
from django.db import transaction

from addon_service.addon_imp.instantiation import get_storage_addon_instance
from addon_service.common.dibs import dibs
from addon_service.common.invocation import InvocationStatus
from addon_service.models import AddonOperationInvocation
from addon_toolkit.json_arguments import json_for_typed_value


__all__ = (
    "perform_invocation__async",
    "perform_invocation__blocking",
    # TODO: @celery.task(def perform_invocation__celery)
)


def perform_invocation__blocking(
    invocation: AddonOperationInvocation,
) -> AddonOperationInvocation:
    # non-async for django transactions
    with dibs(invocation):  # TODO: handle dibs errors
        try:
            _addon_instance = get_storage_addon_instance(invocation.thru_addon)
            _operation_imp = invocation.operation.operation_imp
            # inner transaction to contain database errors,
            # so status can be saved in the outer transaction (from `dibs`)
            with transaction.atomic():
                _result = _operation_imp.call_with_json_kwargs(
                    _addon_instance,
                    invocation.operation_kwargs,
                )
            invocation.operation_result = json_for_typed_value(
                _operation_imp.declaration.return_type,
                _result,
            )
            invocation.invocation_status = InvocationStatus.SUCCESS
        except BaseException as _e:
            invocation.set_exception(_e)
            raise  # TODO: or swallow?
        finally:
            invocation.save()
    return invocation


perform_invocation__async = sync_to_async(perform_invocation__blocking)
# ^ someday, this may be reversed to `async def perform_invocation__async(...)`
# and `perform_invocation__blocking = async_to_sync(perform_invocation__async)`
