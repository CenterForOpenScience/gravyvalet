'''
nice thoughts:
- single-file addon implementation? aim for simplicity
- use duck-typing to reduce imports, dependencies
    - given a module, look for declared capabilities and adjust expectations
- alternately, lean into rdf as interoperable layer
    - identify capabilities by iri
    - use primitive_metadata? each addon implementation gathers data by request
'''
from addon_service.interfaces import StorageInterface


# each MyStorage method implements a known capability
class MyStorage(StorageInterface):
    def item_download_url(self, item_id: str) -> str:
        # return direct download url (e.g. waterbutler)
        raise NotImplementedError

    def item_upload_url(self, item_id: str) -> str:
        # return direct upload url (e.g. waterbutler)
        raise NotImplementedError


class MyExternalServiceInterface:
    storage = MyStorage
    # compute = MyCompute
    # calendar = MyCalendar
    # citations = MyCitations
