import contextlib
import logging

from django.db import transaction


__all__ = ("dibs",)


_logger = logging.getLogger()


@contextlib.contextmanager
def dibs(model_instance, *, refresh=True):
    """context manager that locks the database row for a given model instance

    a dibs'd block cannot be running twice for the same model instance at the same time
    """
    with transaction.atomic():
        _locked_obj = (
            model_instance.__class__.objects.select_for_update()
            .filter(pk=model_instance.pk)
            .first()
        )
        if _locked_obj is None:
            raise ValueError(f"dibs: could not find {model_instance}")
        _logger.debug("dibs: locked %r", _locked_obj)
        if refresh:  # ensure the original object is up to date
            model_instance.refresh_from_db()
            yield
        else:  # avoid a query, but the original object may be stale
            yield _locked_obj
        _logger.debug("dibs: unlocked %r", _locked_obj)
