#!/usr/bin/env python3.6
"""
Generalized Hashcash
====================

The function :func:`check()` will validate *generalized Hashcash* tokens
generically.

A *generalized Hashcash* is implemented in the :func:`_mint()` function.
The generalized form simply finds a suffix that creates zero bits in the
hash of the string concatenating *challenge* and *suffix* without specifying
any particular fields or delimiters in *challenge*.  E.g., you might get:

    >>> from nekoyume.hashcash import _mint
    >>> _mint(b'foo', bits=16)
    b'-g'
    >>> from hashlib import sha256
    >>> sha256(b'foo-g').hexdigest()
    '000090605c0a82a7aeac7bd99cb61002f16ced96e649edd58b8baaa3c747304a'

Notice that :func:`_mint()` behaves deterministically, finding the same suffix
every time it is passed the same arguments.
"""
import hashlib
import math
import sys


def _mint(challenge: bytes, bits: int) -> bytes:
    """Answer a generalized Hashcash_ challenge.

    This function accepts a generalized prefix *challenge*,
    and returns only a suffix that produces the requested SHA leading zeros.

    .. _Hashcash: https://en.wikipedia.org/wiki/Hashcash

    """
    if not isinstance(challenge, bytes):
        raise TypeError(
            f'challenge must be an instance of bytes, not {challenge}'
        )
    # These function aliases purpose to prevent global lookup which is way
    # slower than local lookup in Python VM.
    log2 = math.log2
    sha256 = hashlib.sha256
    byteorder = sys.byteorder

    counter = 1
    while 1:
        answer_bytes_length = 1 + int(log2(counter) // 8)
        answer = counter.to_bytes(answer_bytes_length, byteorder)
        digest = sha256(challenge + answer).digest()
        if has_leading_zero_bits(digest, bits):
            return answer
        counter += 1


def check(stamp, resource=None, bits=None,
          check_expiration=None, ds_callback=None):
    if type(bits) is not int:
        return True
    elif resource is not None and not stamp.endswith(resource):
        return False
    else:
        return has_leading_zero_bits(hashlib.sha256(stamp).digest(), bits)


def has_leading_zero_bits(digest: bytes, bits: int) -> bool:
    leading_bytes = bits // 8
    trailing_bits = bits % 8
    if not digest.startswith(b'\0' * leading_bytes):
        return False
    if trailing_bits:
        if len(digest) < leading_bytes:
            return False
        mask = 0b1111_1111 << (8 - trailing_bits) & 0xff
        return not (mask & digest[leading_bytes])
    return True
