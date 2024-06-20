"""for encrypting and decrypting data (using secrets from settings)

considering recommendations from:
- https://cryptography.io/en/latest/fernet/
- https://docs.python.org/3.12/library/hashlib.html#hashlib.scrypt
- https://cryptography.io/en/latest/hazmat/primitives/key-derivation-functions/#scrypt
- https://datatracker.ietf.org/doc/html/rfc7914
- https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-132.pdf
"""

import base64
import dataclasses
import functools
import hashlib
import json
import math
import os

from cryptography import fernet
from django.conf import settings


__all__ = (
    "pls_decrypt_bytes",
    "pls_decrypt_json",
    "pls_encrypt_bytes",
    "pls_encrypt_json",
    "salt_factory",
)


# 32-byte key expected by cryptography.fernet.Fernet
_KEY_BYTE_COUNT = 32

# recommended len(salt) >= 16 bytes
_SALT_BYTE_COUNT = settings.GRAVYVALET_SALT_BYTE_COUNT or 17


def salt_factory() -> bytes:
    return os.urandom(_SALT_BYTE_COUNT)


@dataclasses.dataclass(frozen=True)  # frozen for use as lru_cache key
class KeyParameters:  # https://datatracker.ietf.org/doc/html/rfc7914#section-2
    salt: bytes = dataclasses.field(default_factory=salt_factory)
    # recommended scrypt_cost ("N") between 2^14 and 2^20
    scrypt_cost: int = settings.GRAVYVALET_SCRYPT_COST or 2**17
    # recommended scrypt_block_size ("r") = 8
    scrypt_block_size: int = settings.GRAVYVALET_SCRYPT_BLOCK_SIZE or 8
    # recommended scrypt_parallelization ("p") = 1
    scrypt_parallelization: int = settings.GRAVYVALET_SCRYPT_PARALLELIZATION or 1

    def __post_init__(self):
        assert self.scrypt_block_size > 1
        # scrypt_cost "must be larger than 1, a power of 2, and less than 2^(128 * r / 8)"
        _cost_log2 = math.log2(self.scrypt_cost)
        assert (
            self.scrypt_cost > 1
            and _cost_log2 == int(_cost_log2)
            and _cost_log2 <= (128 * self.scrypt_block_size / 8)
        )
        # scrypt_parallelization "is a positive integer less than or equal to ((2^32-1) * 32) / (128 * r)"
        assert self.scrypt_parallelization <= ((2**32 - 1) * 32) / (
            128 * self.scrypt_block_size
        )

    def memory_required(self) -> int:
        return self.scrypt_cost * self.scrypt_block_size * 129


def pls_encrypt_json(jsonable_obj, key_params: KeyParameters) -> bytes:
    return pls_encrypt_bytes(json.dumps(jsonable_obj).encode(), key_params)


def pls_decrypt_json(encrypted_json: bytes, key_params: KeyParameters):
    return json.loads(pls_decrypt_bytes(encrypted_json, key_params))


def pls_encrypt_bytes(msg: bytes, key_params: KeyParameters) -> bytes:
    return _derive_multifernet_key(key_params).encrypt(msg)


def pls_decrypt_bytes(encrypted: bytes, key_params: KeyParameters) -> bytes:
    return _derive_multifernet_key(key_params).decrypt(encrypted)


def pls_rotate_encryption(
    encrypted: bytes,
    stored_params: KeyParameters,
) -> tuple[bytes, KeyParameters]:
    _fresh_params = KeyParameters(salt=salt_factory())
    _stored_up_to_date = (
        len(stored_params.salt) == len(_fresh_params.salt)
        and stored_params.scrypt_cost == _fresh_params.scrypt_cost
        and stored_params.scrypt_block_size == _fresh_params.scrypt_block_size
        and stored_params.scrypt_parallelization == _fresh_params.scrypt_parallelization
    )
    if _stored_up_to_date:  # key params NOT changed -- can use MultiFernet.rotate
        _fresh_encrypted = _derive_multifernet_key(stored_params).rotate(encrypted)
        _fresh_params = stored_params
    else:
        # key defaults HAVE changed -- decrypt and re-encrypt
        _decrypted = pls_decrypt_bytes(encrypted, stored_params)
        _fresh_encrypted = pls_encrypt_bytes(_decrypted, _fresh_params)
    return _fresh_encrypted, _fresh_params


# deriving keys is expensive on purpose -- cache, but only in local memory
@functools.lru_cache(maxsize=settings.GRAVYVALET_DERIVED_KEY_CACHE_SIZE)
def _derive_multifernet_key(
    key_params: KeyParameters,
    /,  # positional-only params for cache-friendliness
) -> fernet.MultiFernet:
    # https://cryptography.io/en/latest/fernet/#cryptography.fernet.MultiFernet
    return fernet.MultiFernet(
        [
            _derive_fernet_key(_secret, key_params)
            for _secret in (
                settings.GRAVYVALET_ENCRYPT_SECRET,
                *settings.GRAVYVALET_ENCRYPT_SECRET_PRIORS,
            )
        ]
    )


def _derive_fernet_key(secret: bytes, key_params: KeyParameters) -> fernet.Fernet:
    # https://cryptography.io/en/latest/fernet/#using-passwords-with-fernet
    return fernet.Fernet(
        base64.urlsafe_b64encode(_derive_key_bytes(secret, key_params))
    )


def _derive_key_bytes(secret: bytes, key_params: KeyParameters) -> bytes:
    return hashlib.scrypt(
        secret,
        salt=key_params.salt,
        n=key_params.scrypt_cost,
        r=key_params.scrypt_block_size,
        p=key_params.scrypt_parallelization,
        dklen=_KEY_BYTE_COUNT,
        maxmem=key_params.memory_required(),
    )
