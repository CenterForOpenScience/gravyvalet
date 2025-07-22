# OSF AzureBlobStorage Addon

### Register the addon with Microsoft at: https://portal.azure.com/#home


1. Search or click "App registrations"
2. Click "+ New registration"
    1. Name: COS AzureBlobStorage App
    2. Supported account types:
         Accounts in any organizational directory (Any Azure AD directory - Multitenant) and personal Microsoft accounts (e.g. Skype, Xbox)
    3. Redirect URI (optional)
         http://localhost:5000/oauth/callback/azureblobstorage/
3. sent to new application registration page
     1. "Note Application (client) ID", to fill it into GV admin
4. Click on "Certificates & secrets"
     1. Click "+ New client secret"
     2. Choose term limits
     3. Save
     4. Copy "Value" of new secret. to fill it into GV admin 
5. Click on "API permissions"
6. Click "+ Add a permission"
     1. Select "Azure Storage"
     2. Select "Delegated Permission"
     3. "user_impersonation" is selected by default.
7. Configure Storage Account IAM Settings
     1. Go to your Storage Account in Azure Portal
     2. Click on "Access Control (IAM)"
     3. Click "+ Add" and select "Add role assignment"
     4. Choose "Storage Blob Data Contributor" role
     5. In "Assign access to", select "User, group, or service principal"
     6. Search and select your registered application name
     7. Click "Review + assign" to save the changes
