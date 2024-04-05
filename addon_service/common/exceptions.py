from django.core.exceptions import ValidationError


class InvalidCredentials(ValidationError):
    def __init__(
        self, credentials_issuer, missing_fields, extra_fields, *args, **kwargs
    ):
        self.credentials_issuer = credentials_issuer
        self.missing_fields = missing_fields
        self.extra_fields = extra_fields
        error_message = (
            f"Supplied credentials for Credentials Issuer {credentials_issuer.name} are not valid "
            f"for Credentials Format {credentials_issuer.credentials_format.name}."
            f"\nThe following required fields are missing: {missing_fields}"
            f"\nThe following unexpected fields were present: {extra_fields}"
        )
        super().__init__(message=error_message, *args, **kwargs)
