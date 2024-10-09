from http import HTTPStatus

from asgiref.sync import async_to_sync
from django.http import HttpResponse

from addon_service.authorized_account.citation.models import AuthorizedCitationAccount
from addon_service.authorized_account.storage.models import AuthorizedStorageAccount
from addon_service.oauth1.utils import get_access_token
from addon_service.osf_models.fields import decrypt_string


def oauth1_callback_view(request):
    oauth_token = request.GET["oauth_token"]
    oauth_verifier = request.GET["oauth_verifier"]

    classname, pk = decrypt_string(request.session.get("oauth1a_account_id")).split("/")
    del request.session["oauth1a_account_id"]
    match classname:
        case "AuthorizedStorageAccount":
            account = AuthorizedStorageAccount.objects.get(pk=pk)
        case "AuthorizedCitationAccount":
            account = AuthorizedCitationAccount.objects.get(pk=pk)

    oauth1_client_config = account.external_service.oauth1_client_config
    final_credentials, other_info = async_to_sync(get_access_token)(
        access_token_url=oauth1_client_config.access_token_url,
        oauth_consumer_key=oauth1_client_config.client_key,
        oauth_consumer_secret=oauth1_client_config.client_secret,
        oauth_token=oauth_token,
        oauth_token_secret=account.temporary_oauth1_credentials.oauth_token_secret,
        oauth_verifier=oauth_verifier,
    )
    account.credentials = final_credentials
    account.save()
    async_to_sync(account.execute_post_auth_hook)(other_info)
    return HttpResponse(status=HTTPStatus.OK)  # TODO: redirect
