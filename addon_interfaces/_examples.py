from http import HTTPMethod

from gravyvalet_interfaces import StorageInterface


# TODO: actual implementations
class _ExampleStorageImplementation(StorageInterface):
    # implement method from StorageInterface
    def item_download_url(self, item_id: str) -> str:
        return self._waterbutler_download_url(item_id)

    # implement method from StorageInterface
    async def get_item_description(self, item_id: str):
        yield ("http://purl.org/dc/terms/identifier", item_id)

    # implement method from StorageInterface
    def item_upload_url(self, item_id: str) -> str:
        return self._waterbutler_upload_url(item_id)

    # implement method from StorageInterface
    async def pls_delete_item(self, item_id: str):
        await self.external_request(
            HTTPMethod.DELETE,
            self._external_url(item_id),
        )

    ###
    # private, implementation-specific methods

    def _waterbutler_download_url(self, item_id):
        raise NotImplementedError

    def _waterbutler_upload_url(self, item_id):
        raise NotImplementedError
