from coincurve import PublicKey

from nekoyume.util import get_address


def test_get_address():
    raw_key = bytes.fromhex(
        '04fb0af727d1839557ea5214a7b7dd799c05dab9da63329a6c6d9836fd19a29ce'
        'bc34f7ba31877b22f6767bb1d9f376a33fc0f28f37ada368611b011c01dbef90f'
    )
    pubkey = PublicKey(raw_key)
    assert '0x80e0b0a7cc8001086a37648f993b2bd855d0ab59' == get_address(pubkey)
