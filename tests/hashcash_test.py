import hashlib
import os

from pytest import mark

from nekoyume.hashcash import check, _mint


@mark.parametrize('challenge', [os.urandom(40) for _ in range(5)])
@mark.parametrize('bits', range(4, 17, 4))
def test_mint(challenge, bits):
    answer = _mint(challenge.hex(), bits)
    stamp = challenge.hex() + answer
    digest = hashlib.sha256(stamp.encode())
    assert digest.hexdigest().startswith('0' * (bits // 4))
    assert check(stamp)
