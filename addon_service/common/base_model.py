from django.db import models
from django.utils import timezone


class AddonsServiceBaseModel(models.Model):
    created = models.DateTimeField(editable=False)
    modified = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.id:
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
