import datetime

from coincurve import PublicKey
from pytest import mark

from nekoyume.util import deserialize_datetime, get_address


def test_get_address():
    raw_key = bytes.fromhex(
        '04fb0af727d1839557ea5214a7b7dd799c05dab9da63329a6c6d9836fd19a29ce'
        'bc34f7ba31877b22f6767bb1d9f376a33fc0f28f37ada368611b011c01dbef90f'
    )
    pubkey = PublicKey(raw_key)
    assert '0x80e0b0a7cc8001086a37648f993b2bd855d0ab59' == get_address(pubkey)


@mark.parametrize('time, expected', [
    ('2018-10-31 15:42:08', datetime.datetime(2018, 10, 31, 15, 42, 8)),
    (
        '2018-10-31 15:42:20.301968',
        datetime.datetime(2018, 10, 31, 15, 42, 20, 301968)
    ),
])
def test_deserialized_datetime(time, expected):
    assert deserialize_datetime(time) == expected
