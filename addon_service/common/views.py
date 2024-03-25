from django.views import View
from django.utils import timezone
from django.shortcuts import redirect
from addon_service.models import ExternalAccount, ExternalCredentials, AuthorizedStorageAccount, ExternalStorageService


class OauthCallbackView(View):
    def get(self, request):
        state = request.GET.get("state")
        account_owner = request.user
        external_storage_service, data = ExternalStorageService.get_ess_and_data_from_code(request)

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

        return redirect(state)
