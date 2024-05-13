from django.contrib.postgres.fields import ArrayField
from django.db import models
from osf_models.fields import (
    DateTimeAwareJSONField,
    EncryptedTextField,
)


class ExternalAccount(models.Model):
    """An account on an external service.

    Note that this object is not and should not be aware of what other objects
    are associated with it. This is by design, and this object should be kept as
    thin as possible, containing only those fields that must be stored in the
    database.

    The ``provider`` field is a de facto foreign key to an ``ExternalProvider``
    object, as providers are not stored in the database.
    """

    # The OAuth credentials. One or both of these fields should be populated.
    # For OAuth1, this is usually the "oauth_token"
    # For OAuth2, this is usually the "access_token"
    oauth_key = EncryptedTextField(blank=True, null=True)

    # For OAuth1, this is usually the "oauth_token_secret"
    # For OAuth2, this is not used
    oauth_secret = EncryptedTextField(blank=True, null=True)

    # Used for OAuth2 only
    refresh_token = EncryptedTextField(blank=True, null=True)
    date_last_refreshed = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    scopes = ArrayField(models.CharField(max_length=128), default=list, blank=True)

    # The `name` of the service
    # This lets us query for only accounts on a particular provider
    # TODO We should make provider an actual FK someday.
    provider = models.CharField(max_length=50, blank=False, null=False)
    # The proper 'name' of the service
    # Needed for account serialization
    provider_name = models.CharField(max_length=255, blank=False, null=False)

    # The unique, persistent ID on the remote service.
    provider_id = models.CharField(max_length=255, blank=False, null=False)

    # The user's name on the external service
    display_name = EncryptedTextField(blank=True, null=True)
    # A link to the user's profile on the external service
    profile_url = EncryptedTextField(blank=True, null=True)

    class Meta:
        managed = False

class BaseOAuthNodeSettings(models.Model):
    class Meta:
        abstract = True
        managed = False

    external_account = models.ForeignKey(ExternalAccount, null=True, blank=True,
                                         related_name='%(app_label)s_node_settings',
                                         on_delete=models.CASCADE)

class BaseOAuthUserSettings(models.Model):
    class Meta:
        abstract = True
        managed = False
    
    # Keeps track of what nodes have been given permission to use external
    #   accounts belonging to the user.
    oauth_grants = DateTimeAwareJSONField(default=dict, blank=True)
    # example:
    # {
    #     '<Node._id>': {
    #         '<ExternalAccount._id>': {
    #             <metadata>
    #         },
    #     }
    # }
    #
    # metadata here is the specific to each addon.

class BitbucketUserSettings(BaseOAuthUserSettings):
    #TODO: specify which db table?

class BitbucketNodeSettings(BaseOAuthNodeSettings):
    user = models.TextField(blank=True, null=True)
    repo = models.TextField(blank=True, null=True)
    hook_id = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(BitbucketUserSettings, null=True, blank=True, on_delete=models.CASCADE)

class BoaUserSettings(BaseOAuthUserSettings):
    #TODO: specify which db table?

class BoaNodeSettings(BaseOAuthNodeSettings):
    folder_id = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(BoaUserSettings, null=True, blank=True, on_delete=models.CASCADE)

class BoxUserSettings(BaseOAuthUserSettings):
    #TODO: specify which db table?

class BoxNodeSettings(BaseOAuthNodeSettings):
    folder_id = models.TextField(null=True, blank=True)
    folder_name = models.TextField(null=True, blank=True)
    folder_path = models.TextField(null=True, blank=True)
    user_settings = models.ForeignKey(BoxUserSettings, null=True, blank=True, on_delete=models.CASCADE)

class DataverseUserSettings(BaseOAuthUserSettings):
    #TODO: specify which db table?

class DataverseNodeSettings(BaseOAuthNodeSettings):
    dataverse_alias = models.TextField(blank=True, null=True)
    dataverse = models.TextField(blank=True, null=True)
    dataset_doi = models.TextField(blank=True, null=True)
    _dataset_id = models.TextField(blank=True, null=True)
    dataset = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(DataverseUserSettings, null=True, blank=True, on_delete=models.CASCADE)

class DropboxUserSettings(BaseOAuthUserSettings):
    #TODO: specify which db table?

class DropboxNodeSettings(BaseOAuthNodeSettings):
    folder = models.TextField(null=True, blank=True)
    user_settings = models.ForeignKey(DropboxUserSettings, null=True, blank=True, on_delete=models.CASCADE)

class FigshareUserSettings(BaseOAuthUserSettings):
    #TODO: specify which db table?

class FigshareUserSettings(BaseOAuthNodeSettings):
    folder_id = models.TextField(blank=True, null=True)
    folder_name = models.TextField(blank=True, null=True)
    folder_path = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(FigshareUserSettings, null=True, blank=True, on_delete=models.CASCADE)

class GithubUserSettings(BaseOAuthUserSettings):
    #TODO: specify which db table?

class GithubNodeSettings(BaseOAuthNodeSettings):
    user = models.TextField(blank=True, null=True)
    repo = models.TextField(blank=True, null=True)
    hook_id = models.TextField(blank=True, null=True)
    hook_secret = models.TextField(blank=True, null=True)
    registration_data = DateTimeAwareJSONField(default=dict, blank=True, null=True)
    user_settings = models.ForeignKey(GithubUserSettings, null=True, blank=True, on_delete=models.CASCADE)

class GitlabUserSettings(BaseOAuthUserSettings):
    #TODO: specify which db table?

class GitlabNodeSettings(BaseOAuthNodeSettings):
    user = models.TextField(blank=True, null=True)
    repo = models.TextField(blank=True, null=True)
    repo_id = models.TextField(blank=True, null=True)
    hook_id = models.TextField(blank=True, null=True)
    hook_secret = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(GitlabUserSettings, null=True, blank=True, on_delete=models.CASCADE)

class GoogleDriveUserSettings(BaseOAuthUserSettings):
    #TODO: specify which db table?

class GoogleDriveNodeSettings(BaseOAuthNodeSettings):
    older_id = models.TextField(null=True, blank=True)
    folder_path = models.TextField(null=True, blank=True)
    user_settings = models.ForeignKey(GoogleDriveUserSettings, null=True, blank=True, on_delete=models.CASCADE)

class MendeleyUserSettings(BaseOAuthUserSettings):
    #TODO: specify which db table?

class MendeleyNodeSettings(BaseOAuthNodeSettings):
    list_id = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(MendeleyUserSettings, null=True, blank=True, on_delete=models.CASCADE)

class OneDriveUserSettings(BaseOAuthUserSettings):
    #TODO: specify which db table?

class OneDriveNodeSettings(BaseOAuthNodeSettings):
    folder_id = models.TextField(null=True, blank=True)
    folder_path = models.TextField(null=True, blank=True)
    drive_id = models.TextField(null=True, blank=True)
    user_settings = models.ForeignKey(OneDriveUserSettings, null=True, blank=True, on_delete=models.CASCADE)

class OwnCloudUserSettings(BaseOAuthUserSettings):
    #TODO: specify which db table?

class OwnCloudNodeSettings(BaseOAuthNodeSettings):
    folder_id = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(OwnCloudUserSettings, null=True, blank=True, on_delete=models.CASCADE)

class S3UserSettings(BaseOAuthUserSettings):
    #TODO: specify which db table?

class S3NodeSettings(BaseOAuthNodeSettings):
    folder_id = models.TextField(blank=True, null=True)
    folder_name = models.TextField(blank=True, null=True)
    encrypt_uploads = models.BooleanField(default=True)
    user_settings = models.ForeignKey(S3UserSettings, null=True, blank=True, on_delete=models.CASCADE)

class ZoteroUserSettings(BaseOAuthUserSettings):
    #TODO: specify which db table?

class ZoteroNodeSettings(BaseOAuthNodeSettings):
    list_id = models.TextField(blank=True, null=True)
    library_id = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(ZoteroUserSettings, null=True, blank=True, on_delete=models.CASCADE)