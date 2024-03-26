import aiohttp
from asgiref.sync import (
    async_to_sync,
    sync_to_async,
)
from django.db import transaction

from addon_service.addon_imp.instantiation import get_storage_addon_instance
from addon_service.common.dibs import dibs
from addon_service.common.invocation import InvocationStatus
from addon_service.models import AddonOperationInvocation
from addon_toolkit.json_arguments import json_for_typed_value


__all__ = (
    "perform_invocation__blocking",
    # TODO: async def perform_invocation__async
    # TODO: @celery.task(def perform_invocation__celery)
)


def perform_invocation__blocking(
    invocation: AddonOperationInvocation,
    addon_instance: object,
) -> AddonOperationInvocation:
    # non-async for django transactions
    with dibs(invocation):  # TODO: handle dibs errors
        try:
            _operation_imp = invocation.operation.operation_imp
            # wrap in a transaction to contain database errors,
            # so status can be saved in the outer transaction
            with transaction.atomic():
                _result = _operation_imp.call_with_json_kwargs(
                    addon_instance,
                    invocation.operation_kwargs,
                )
        except BaseException as _e:
            invocation.operation_result = None
            invocation.invocation_status = InvocationStatus.PROBLEM
            print(_e)
            # TODO: save message/traceback
            raise
        else:  # no errors
            invocation.operation_result = json_for_typed_value(
                _operation_imp.declaration.return_dataclass,
                _result,
            )
            invocation.invocation_status = InvocationStatus.SUCCESS
        finally:
            invocation.save()
            return invocation


perform_invocation__async = sync_to_async(perform_invocation__blocking)


async def full_perform__async(invocation: AddonOperationInvocation):
    # TODO: reuse sessions?
    async with aiohttp.ClientSession() as _session:
        _addon_instance = get_storage_addon_instance(
            _session,
            invocation.thru_addon,
        )  # TODO: consistent imp_cls instantiation (with params, probably)
        perform_invocation__blocking(invocation, _addon_instance)


full_perform__blocking = async_to_sync(full_perform__async)
