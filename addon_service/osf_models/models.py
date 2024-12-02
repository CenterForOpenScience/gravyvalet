from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import CharField

from addon_service.osf_models.fields import (
    DateTimeAwareJSONField,
    EncryptedTextField,
)


class Model(models.Model):
    class Meta:
        abstract = True
        managed = False
        app_label = "osf"


class ExternalAccount(Model):
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
        app_label = "osf"
        db_table = "osf_externalaccount"


class Guid(Model):
    _id = CharField()
    content_type_id = models.IntegerField()
    object_id = models.IntegerField()

    class Meta:
        db_table = "osf_guid"
        managed = False
        app_label = "osf"


class OsfUser(Model):
    @property
    def guid(self):
        return Guid.objects.filter(content_type_id=70, object_id=self.id).first()._id

    class Meta:
        db_table = "osf_osfuser"
        managed = False
        app_label = "addons"


class UserToExternalAccount(Model):
    osfuser = models.ForeignKey(OsfUser, on_delete=models.CASCADE)
    externalaccount = models.ForeignKey(ExternalAccount, on_delete=models.CASCADE)

    class Meta:
        db_table = "osf_osfuser_external_accounts"
        managed = False
        app_label = "addons"


class BaseOAuthNodeSettings(Model):
    class Meta:
        abstract = True
        managed = False

    # Node to which these settings are bound to
    owner_id = models.IntegerField()
    external_account = models.ForeignKey(
        ExternalAccount,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )


class BaseOAuthUserSettings(Model):
    class Meta:
        abstract = True
        managed = False

    # Keeps track of what nodes have been given permission to use external
    #   accounts belonging to the user.
    owner_id = models.IntegerField(blank=True, null=True)
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
    class Meta:
        db_table = "addons_bitbucket_usersettings"


class BitbucketNodeSettings(BaseOAuthNodeSettings):
    class Meta:
        db_table = "addons_bitbucket_nodesettings"
        managed = False
        app_label = "addons"

    user = models.TextField(blank=True, null=True)
    repo = models.TextField(blank=True, null=True)
    hook_id = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(
        BitbucketUserSettings, null=True, blank=True, on_delete=models.CASCADE
    )


class BoaUserSettings(BaseOAuthUserSettings):
    class Meta:
        db_table = "addons_boa_usersettings"


class BoaNodeSettings(BaseOAuthNodeSettings):
    class Meta:
        db_table = "addons_boa_nodesettings"
        managed = False
        app_label = "addons"

    folder_id = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(
        BoaUserSettings, null=True, blank=True, on_delete=models.CASCADE
    )


class BoxUserSettings(BaseOAuthUserSettings):
    class Meta:
        db_table = "addons_box_usersettings"


class BoxNodeSettings(BaseOAuthNodeSettings):
    class Meta:
        db_table = "addons_box_nodesettings"
        managed = False
        app_label = "addons"

    folder_id = models.TextField(null=True, blank=True)
    folder_name = models.TextField(null=True, blank=True)
    folder_path = models.TextField(null=True, blank=True)
    user_settings = models.ForeignKey(
        BoxUserSettings, null=True, blank=True, on_delete=models.CASCADE
    )


class DataverseUserSettings(BaseOAuthUserSettings):
    class Meta:
        db_table = "addons_dataverse_usersettings"


class DataverseNodeSettings(BaseOAuthNodeSettings):
    class Meta:
        db_table = "addons_dataverse_nodesettings"
        managed = False
        app_label = "addons"

    dataverse_alias = models.TextField(blank=True, null=True)
    dataverse = models.TextField(blank=True, null=True)
    dataset_doi = models.TextField(blank=True, null=True)
    _dataset_id = models.TextField(blank=True, null=True)
    dataset = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(
        DataverseUserSettings, null=True, blank=True, on_delete=models.CASCADE
    )


class DropboxUserSettings(BaseOAuthUserSettings):
    class Meta:
        db_table = "addons_dropbox_usersettings"


class DropboxNodeSettings(BaseOAuthNodeSettings):
    class Meta:
        db_table = "addons_dropbox_nodesettings"
        managed = False
        app_label = "addons"

    folder = models.TextField(null=True, blank=True)
    user_settings = models.ForeignKey(
        DropboxUserSettings, null=True, blank=True, on_delete=models.CASCADE
    )


class FigshareUserSettings(BaseOAuthUserSettings):
    class Meta:
        db_table = "addons_figshare_usersettings"


class FigshareNodeSettings(BaseOAuthNodeSettings):
    class Meta:
        db_table = "addons_figshare_nodesettings"
        managed = False
        app_label = "addons"

    folder_id = models.TextField(blank=True, null=True)
    folder_name = models.TextField(blank=True, null=True)
    folder_path = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(
        FigshareUserSettings, null=True, blank=True, on_delete=models.CASCADE
    )


class GithubUserSettings(BaseOAuthUserSettings):
    class Meta:
        db_table = "addons_github_usersettings"


class GithubNodeSettings(BaseOAuthNodeSettings):
    class Meta:
        db_table = "addons_github_nodesettings"
        managed = False
        app_label = "addons"

    user = models.TextField(blank=True, null=True)
    repo = models.TextField(blank=True, null=True)
    hook_id = models.TextField(blank=True, null=True)
    hook_secret = models.TextField(blank=True, null=True)
    registration_data = DateTimeAwareJSONField(default=dict, blank=True, null=True)
    user_settings = models.ForeignKey(
        GithubUserSettings, null=True, blank=True, on_delete=models.CASCADE
    )


class GitlabUserSettings(BaseOAuthUserSettings):
    class Meta:
        db_table = "addons_gitlab_usersettings"


class GitlabNodeSettings(BaseOAuthNodeSettings):
    class Meta:
        db_table = "addons_gitlab_nodesettings"
        managed = False
        app_label = "addons"

    user = models.TextField(blank=True, null=True)
    repo = models.TextField(blank=True, null=True)
    repo_id = models.TextField(blank=True, null=True)
    hook_id = models.TextField(blank=True, null=True)
    hook_secret = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(
        GitlabUserSettings, null=True, blank=True, on_delete=models.CASCADE
    )


class GoogleDriveUserSettings(BaseOAuthUserSettings):
    class Meta:
        db_table = "addons_googledrive_usersettings"


class GoogleDriveNodeSettings(BaseOAuthNodeSettings):
    class Meta:
        db_table = "addons_googledrive_nodesettings"
        managed = False
        app_label = "addons"

    folder_id = models.TextField(null=True, blank=True)
    folder_path = models.TextField(null=True, blank=True)
    user_settings = models.ForeignKey(
        GoogleDriveUserSettings, null=True, blank=True, on_delete=models.CASCADE
    )


class MendeleyUserSettings(BaseOAuthUserSettings):
    class Meta:
        db_table = "addons_mendeley_usersettings"


class MendeleyNodeSettings(BaseOAuthNodeSettings):
    class Meta:
        db_table = "addons_mendeley_nodesettings"
        managed = False
        app_label = "addons"

    list_id = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(
        MendeleyUserSettings, null=True, blank=True, on_delete=models.CASCADE
    )


class OneDriveUserSettings(BaseOAuthUserSettings):
    class Meta:
        db_table = "addons_onedrive_usersettings"


class OneDriveNodeSettings(BaseOAuthNodeSettings):
    class Meta:
        db_table = "addons_onedrive_nodesettings"
        managed = False
        app_label = "addons"

    folder_id = models.TextField(null=True, blank=True)
    folder_path = models.TextField(null=True, blank=True)
    drive_id = models.TextField(null=True, blank=True)
    user_settings = models.ForeignKey(
        OneDriveUserSettings, null=True, blank=True, on_delete=models.CASCADE
    )


class OwnCloudUserSettings(BaseOAuthUserSettings):
    class Meta:
        db_table = "addons_owncloud_usersettings"


class OwnCloudNodeSettings(BaseOAuthNodeSettings):
    class Meta:
        db_table = "addons_owncloud_nodesettings"
        managed = False
        app_label = "addons"

    folder_id = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(
        OwnCloudUserSettings, null=True, blank=True, on_delete=models.CASCADE
    )


class S3UserSettings(BaseOAuthUserSettings):
    class Meta:
        db_table = "addons_s3_usersettings"


class S3NodeSettings(BaseOAuthNodeSettings):
    class Meta:
        db_table = "addons_s3_nodesettings"
        managed = False
        app_label = "addons"

    folder_id = models.TextField(blank=True, null=True)
    folder_name = models.TextField(blank=True, null=True)
    encrypt_uploads = models.BooleanField(default=True)
    user_settings = models.ForeignKey(
        S3UserSettings, null=True, blank=True, on_delete=models.CASCADE
    )


class ZoteroUserSettings(BaseOAuthUserSettings):
    class Meta:
        db_table = "addons_zotero_usersettings"


class ZoteroNodeSettings(BaseOAuthNodeSettings):
    class Meta:
        db_table = "addons_zotero_nodesettings"
        managed = False
        app_label = "addons"

    list_id = models.TextField(blank=True, null=True)
    library_id = models.TextField(blank=True, null=True)
    user_settings = models.ForeignKey(
        ZoteroUserSettings, null=True, blank=True, on_delete=models.CASCADE
    )
