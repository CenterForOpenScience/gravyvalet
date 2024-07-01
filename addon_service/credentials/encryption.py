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
    # recommended scrypt_cost_log2 between 14 and 20 (for "N" between 2^14 and 2^20)
    scrypt_cost_log2: int = settings.GRAVYVALET_SCRYPT_COST_LOG2 or 17
    # recommended scrypt_block_size ("r") = 8
    scrypt_block_size: int = settings.GRAVYVALET_SCRYPT_BLOCK_SIZE or 8
    # recommended scrypt_parallelization ("p") = 1
    scrypt_parallelization: int = settings.GRAVYVALET_SCRYPT_PARALLELIZATION or 1

    def __post_init__(self):
        if len(self.salt) < 16:
            raise ValueError(f"expected salt length >= 16 (got {len(self.salt)})")
        if self.scrypt_block_size <= 1:
            raise ValueError(
                f"expected scrypt_block_size > 1 (got {self.scrypt_block_size})"
            )
        if not (
            self.scrypt_cost_log2 >= 1
            and self.scrypt_cost_log2 == int(self.scrypt_cost_log2)
            and self.scrypt_cost_log2 <= (128 * self.scrypt_block_size / 8)
        ):
            raise ValueError(
                f"expected scrypt_cost_log2 integer between 1 and (128 * r / 8) (got {self.scrypt_cost_log2})"
            )
        if not (
            0
            < self.scrypt_parallelization
            <= ((2**32 - 1) * 32) / (128 * self.scrypt_block_size)
        ):
            raise ValueError(
                f"expected scrypt_parallelization >0 and <=(((2^32-1) * 32) / (128 * r)) (got {self.scrypt_parallelization})"
            )

    def memory_required(self) -> int:
        # approximate upper-bound on scrypt memory usage:
        # - actual block size in bytes: 128 * r
        _block_bytecount = 128 * self.scrypt_block_size
        # - primary memory bottleneck: "scryptROMix Algorithm" https://datatracker.ietf.org/doc/html/rfc7914#section-5
        #   uses an (implicit, temporary) array "V" consisting of N blocks
        _scryptromix_bytecount = (2**self.scrypt_cost_log2) * _block_bytecount
        # - "scrypt Algorithm" https://datatracker.ietf.org/doc/html/rfc7914#section-6
        #   uses "an array B consisting of p blocks of 128 * r octets each"
        _scrypt_main_bytecount = self.scrypt_parallelization * _block_bytecount
        # - add fudge for intermediate blocks and other implementation details
        #   (seems to work well enough for N in range 2^14-2^20, r in range 2-13, p in range 1-5)
        _fudge = _block_bytecount * 5
        return _scrypt_main_bytecount + _scryptromix_bytecount + _fudge


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
        and stored_params.scrypt_cost_log2 == _fresh_params.scrypt_cost_log2
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
    if not settings.GRAVYVALET_ENCRYPT_SECRET:
        raise RuntimeError(
            "gravyvalet can not keep your secrets without a GRAVYVALET_ENCRYPT_SECRET"
            " -- ideally chosen by strong randomness, with around 256 bits of entropy"
            " (e.g. 64 hex digits; 60 d20 rolls; 20 words of a 10000-word vocabulary)"
        )
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
        n=2**key_params.scrypt_cost_log2,
        r=key_params.scrypt_block_size,
        p=key_params.scrypt_parallelization,
        dklen=_KEY_BYTE_COUNT,
        maxmem=key_params.memory_required(),
    )
