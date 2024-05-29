import base64


def make_opaque(key: str) -> str:
    """make a reversible opaque id for the given key

    NOT secure in any way, just meant to discourage applying semantic value to ids
    """
    return base64.urlsafe_b64encode(str(key).encode()).decode()


def unmake_opaque(opaque_key: str) -> str:
    """reverse a reversible opaque id created by `make_opaque`"""
    return base64.urlsafe_b64decode(opaque_key.encode()).decode()
