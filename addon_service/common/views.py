from django.utils import timezone
from rest_framework.views import View
from addon_service.models import (
    ExternalAccount,
    ExternalStorageService,
    ExternalCredentials,
    AuthorizedStorageAccount
)
from django.shortcuts import redirect


class OauthCallbackView(View):
    """
    Handles oauth callbacks for the GV
    """
    authentication_classes = ()  # TODO: many options but safest just to whitelist providers I think
    permission_classes = ()

    def get(self, request):
        state = request.GET.get("state")  # TODO: we can send much with this, but with one url, we must send the Ess id
        account_owner = request.user
        external_storage_service = ExternalStorageService.objects.get(id=state)

        data = external_storage_service.get_oauth_data_from_request(request)

        external_credentials = ExternalCredentials.objects.create(
            oauth_key=data['key'],
            oauth_secret=data.get('secret'),
            expires_at=data.get('expires_at'),
            refresh_token=data.get('refresh_token'),
            date_last_refreshed=timezone.now(),
        )

        external_account, _ = ExternalAccount.objects.get_or_create(
            owner=account_owner,
            credentials=external_credentials,
            credentials_issuer=external_storage_service.credentials_issuer,
        )

        AuthorizedStorageAccount.objects.create(
            external_storage_service=external_storage_service,
            external_account=external_account,
        )

        return redirect(state)  # TODO: This is one of the few UX facing things we will control from GV, make this configurable
