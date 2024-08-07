import boto3
from botocore import exceptions as BotoExceptions
from django.core.exceptions import ValidationError

# from addon_toolkit.cursor import OffsetCursor
from addon_toolkit.interfaces import storage


class S3StorageImp(storage.StorageAddonClientRequestorImp):
    """storage on Amazon S3"""

    @classmethod
    def confirm_credentials(cls, credentials):
        access_key = credentials.access_key
        secret_key = credentials.secret_key
        s3 = boto3.client(
            "s3", aws_access_key_id=access_key, aws_secret_access_key=secret_key
        )
        try:
            s3.list_buckets()
        except BotoExceptions.ClientError:
            raise ValidationError("Fail to validate access key and secret key")

    def create_client(self, credentials):
        access_key = credentials.access_key
        secret_key = credentials.secret_key
        return boto3.client(
            "s3", aws_access_key_id=access_key, aws_secret_access_key=secret_key
        )

    async def get_item_info(self, item_id: str) -> storage.ItemResult:
        if item_id and "/" in item_id:
            # All item_ids should contain a '/'
            bucket, key = item_id.split("/", 1)
            if key:
                # This is item in a bucket
                response = self.client.list_objects(
                    Bucket=bucket, Prefix=key, Delimiter="/"
                )
                if response.get("Contents"):
                    if (
                        len(response["Contents"]) == 1
                        and ("CommonPrefixes" not in response)
                        and (not response["Contents"][0]["Key"].endswith("/"))
                    ):
                        # that means this is a file, not a folder
                        return storage.ItemResult(
                            item_id=response["Contents"][0]["Key"],
                            item_name=response["Contents"][0]["Key"],
                            item_type=storage.ItemType.FILE,
                        )
                    return storage.ItemResult(
                        item_id=item_id,
                        item_name=item_id,
                        item_type=storage.ItemType.FOLDER,
                    )
            else:
                # That means the item_id could be pointing to a bucket
                try:
                    # see if the bucket exists
                    self.client.head_bucket(
                        Bucket=item_id.strip("/"),
                    )
                    return storage.ItemResult(
                        item_id=item_id,
                        item_name=item_id,
                        item_type=storage.ItemType.FOLDER,
                    )
                except BotoExceptions.ClientError:
                    pass
        return None

    async def list_root_items(self, page_cursor: str = "") -> storage.ItemSampleResult:
        results = list(self.list_buckets())
        return storage.ItemSampleResult(
            items=results,
            total_count=len(results),
        )

    async def list_child_items(
        self,
        item_id: str,
        page_cursor: str = "",
        item_type: storage.ItemType | None = None,
    ) -> storage.ItemSampleResult:
        bucket = item_id.split("/", 1)[0]
        key = item_id.split("/", 1)[1]
        if key.endswith("/"):
            # That means this is a folder
            response = self.client.list_objects(
                Bucket=bucket, Prefix=key, Delimiter="/"
            )
            results = []
            if response.get("CommonPrefixes") and (
                item_type is not storage.ItemType.FILE or item_type is None
            ):
                for folder in response["CommonPrefixes"]:
                    results.append(
                        storage.ItemResult(
                            item_id=folder["Prefix"],
                            item_name=folder["Prefix"],
                            item_type=storage.ItemType.FOLDER,
                        )
                    )
            if response.get("Contents") and (
                item_type is not storage.ItemType.FOLDER or item_type is None
            ):
                for file in response["Contents"]:
                    results.append(
                        storage.ItemResult(
                            item_id=file["Key"],
                            item_name=file["Key"],
                            item_type=storage.ItemType.FILE,
                        )
                    )
            return storage.ItemSampleResult(
                items=results,
                total_count=len(results),
            )
        return None

    def list_buckets(self):
        for bucket in self.client.list_buckets()["Buckets"]:
            yield storage.ItemResult(
                item_id=bucket["Name"] + "/",
                item_name=bucket["Name"] + "/",
                item_type=storage.ItemType.FOLDER,
            )
