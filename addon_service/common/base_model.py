from django.db import models
from django.utils import timezone

from addon_service.common.str_uuid_field import (
    StrUUIDField,
    str_uuid4,
)


class AddonsServiceBaseModel(models.Model):
    """common base class for all addon_service models"""

    id = StrUUIDField(primary_key=True, default=str_uuid4, editable=False)
    created = models.DateTimeField(editable=False)
    modified = models.DateTimeField()

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.created = timezone.now()
        self.modified = timezone.now()
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"<{self.__class__.__qualname__}(pk={self.pk})>"

    def __repr__(self):
        return self.__str__()

    class Meta:
        abstract = True
