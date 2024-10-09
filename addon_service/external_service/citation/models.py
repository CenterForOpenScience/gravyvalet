from addon_service.common.validators import validate_citation_imp_number
from addon_service.external_service.models import ExternalService


class ExternalCitationService(ExternalService):

    def clean(self):
        super().clean()
        validate_citation_imp_number(self.int_addon_imp)

    class Meta:
        verbose_name = "External Citation Service"
        verbose_name_plural = "External Citation Services"
        app_label = "addon_service"

    class JSONAPIMeta:
        resource_name = "external-citation-services"
