import functools
from typing import Callable

from coincurve import PublicKey
from keccak import sha3_256

from nekoyume.exc import InvalidMoveError


def get_address(public_key: PublicKey) -> str:
    """Derive an Ethereum-style address from the given public key."""
    return '0x' + sha3_256(public_key.format(False)[1:]).hexdigest()[-40:]


def ensure_block(f: Callable) -> Callable:
    @functools.wraps(f)
    def decorator(self, *args, **kwargs):
        try:
            assert self.block
        except AssertionError:
            raise InvalidMoveError
        return f(self, *args, **kwargs)
    return decorator
