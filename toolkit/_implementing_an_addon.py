"""
nice thoughts:
- single-file addon implementation? aim for simplicity
- various implementation paths...
    - could provide an explicit base class to implement
        - declare capabilities by overriding methods
    - could use duck-typing to reduce imports, dependencies
        - given a module, look for declared capabilities and adjust expectations
        - idea: set iri attrs on the module, leaning into rdf for interoperability
            - identify capabilities by iri
    - could use experimental-but-used-in-share primitive_metadata.gather
"""
from addon_service.interfaces import StorageInterface


# each MyStorage method implements a known capability
class MyStorage(StorageInterface):
    def item_download_url(self, item_id: str) -> str:
        # return direct download url (e.g. waterbutler)
        raise NotImplementedError

    def item_upload_url(self, item_id: str) -> str:
        # return direct upload url (e.g. waterbutler)
        raise NotImplementedError

    async def get_item_infoladle(self, item_id: str) -> dict:
        # send request to external service, return whatever requested info
        # (presumed to load a small amount of metadata -- use waterbutler for download)
        raise NotImplementedError

    # when an api request comes in, check:
    # AuthorizedStorageAccount.authorized_capability_set
    # ConfiguredStorageAddon.configured_capability_set
    # InternalResource.
    async def pls_delete(self, item_id):
        pass


class MyExternalServiceInterface:
    storage = MyStorage
    # compute = MyCompute
    # calendar = MyCalendar
    # citations = MyCitations
