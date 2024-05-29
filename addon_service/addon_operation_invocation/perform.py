from asgiref.sync import (
    async_to_sync,
    sync_to_async,
)
from django.db import transaction

from addon_service.addon_imp.instantiation import get_storage_addon_instance
from addon_service.common.dibs import dibs
from addon_service.common.invocation_status import InvocationStatus
from addon_service.models import AddonOperationInvocation
from addon_toolkit.json_arguments import json_for_typed_value


__all__ = (
    "perform_invocation__async",
    "perform_invocation__blocking",
    # TODO: @celery.task(def perform_invocation__celery)
)


@sync_to_async
def perform_invocation__async(invocation: AddonOperationInvocation) -> None:
    # implemented as a sync function (for django transactions)
    # wrapped in sync_to_async (to guarantee a running event loop)
    with dibs(invocation):  # TODO: handle dibs errors
        try:
            _thru = invocation.thru_addon or invocation.thru_account
            _imp = get_storage_addon_instance(
                _thru.imp_cls,
                invocation.thru_account,
                _thru.storage_imp_config(),
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
                _operation.declaration.return_type,
                _result,
            )
            invocation.invocation_status = InvocationStatus.SUCCESS
        except BaseException as _e:
            invocation.set_exception(_e)
            raise  # TODO: or swallow?
        finally:
            invocation.save()


# NOTE: yes this is `async_to_sync(sync_to_async(...))`; was an easy way
# to guarantee a running event loop when called in a synchronous context
perform_invocation__blocking = async_to_sync(perform_invocation__async)
