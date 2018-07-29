import hashlib
import os

from pytest import mark

from nekoyume.hashcash import check, has_leading_zero_bits, _mint


@mark.parametrize('challenge', [os.urandom(40) for _ in range(5)])
@mark.parametrize('bits', range(4, 17, 4))
def test_mint(challenge, bits):
    answer = _mint(challenge, bits)
    stamp = challenge + answer
    digest = hashlib.sha256(stamp)
    assert has_leading_zero_bits(digest.digest(), bits)
    assert check(stamp)


def test_has_leading_zero_bits():
    def f(digest: bytes, bits: int) -> bool:
        print(  # noqa: T001
            f'Expect leading {bits} zero bits in the {digest!r} '
            f'({digest.hex()} = {" ".join(f"{b:08b}" for b in digest)})'
        )
        return has_leading_zero_bits(digest, bits)
    assert f(b'\x80abc', 0)
    assert not f(b'\x80abc', 1)
    for bits in range(9):
        assert f(b'\0\x80', bits)
    assert not f(b'\0\x80', 9)
    assert f(b'\0\x7f', 9)
    assert not f(b'\0\x7f', 10)
    assert f(b'\0?', 10)
