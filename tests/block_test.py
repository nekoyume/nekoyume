import typing

from pytest import mark, raises
from pytest_localserver.http import WSGIServer
from requests_mock import Mocker
from sqlalchemy.orm.scoping import scoped_session
from sqlalchemy.orm.session import Session
from typeguard import typechecked

from nekoyume.block import Block, find_branch_point
from nekoyume.exc import NodeUnavailable
from nekoyume.move import Move
from nekoyume.node import Node
from nekoyume.user import User


def test_block_validation(fx_user, fx_novice_status):
    move = fx_user.create_novice(fx_novice_status)
    block = Block.create(fx_user, [move])
    assert block.valid
    move.id = ('00000000000000000000000000000000'
               '00000000000000000000000000000000')
    assert not block.valid


def test_sync(fx_user, fx_session, fx_other_user, fx_other_session, fx_server,
              fx_novice_status):
    assert fx_other_session.query(Block).count() == 0
    assert fx_session.query(Block).count() == 0

    Block.sync(Node(url=fx_server.url), fx_other_session)
    assert fx_other_session.query(Block).count() == 0
    assert fx_session.query(Block).count() == 0

    Block.create(fx_other_user, [])
    Block.sync(Node(url=fx_server.url), fx_other_session)
    assert fx_other_session.query(Block).count() == 1
    assert fx_session.query(Block).count() == 0

    move = fx_user.create_novice(fx_novice_status)
    Block.create(fx_user, [move])
    Block.create(fx_user, [])
    Block.create(fx_user, [])

    assert fx_other_session.query(Block).count() == 1
    assert fx_other_session.query(Move).count() == 0
    assert fx_session.query(Block).count() == 3
    assert fx_session.query(Move).count() == 1

    Block.sync(Node(url=fx_server.url), fx_other_session)
    assert fx_other_session.query(Block).count() == 3
    assert fx_other_session.query(Move).count() == 1
    assert fx_session.query(Block).count() == 3
    assert fx_session.query(Move).count() == 1


@typechecked
@mark.parametrize('code', [404, 500, 503])
def test_sync_node_unavailable_on_get_last_block(
        fx_user: User, fx_session: scoped_session,
        fx_other_session: Session, fx_server: WSGIServer,
        fx_novice_status: typing.Mapping[str, str],
        code: int
):
    move = fx_user.create_novice(fx_novice_status)
    Block.create(fx_user, [move])
    with Mocker() as m:
        m.get(url=f'{fx_server.url}/blocks/last', status_code=code)
        Block.sync(Node(url=fx_server.url), fx_other_session)
        assert fx_other_session.query(Block).count() == 0


@typechecked
@mark.parametrize('code', [500, 503])
def test_sync_node_unaviable_on_branch_point(
        fx_user: User, fx_session: scoped_session,
        fx_server: WSGIServer, fx_other_session: Session,
        fx_novice_status: typing.Mapping[str, str],
        code: int
):
    move = fx_user.create_novice(fx_novice_status)
    block = Block.create(fx_user, [move])
    Block.sync(Node(url=fx_server.url), fx_other_session)
    assert fx_other_session.query(Block).count() == 1
    serialized = block.serialize(
        use_bencode=False,
        include_suffix=True,
        include_moves=True,
        include_hash=True
    )
    serialized['id'] = block.id + 1
    with Mocker() as m:
        m.register_uri(
            'GET', f'{fx_server.url}/blocks/last',
            json={'block': serialized},
            status_code=200,
        )
        m.register_uri(
            'GET', f'{fx_server.url}/blocks/1',
            status_code=code,
        )
        assert not Block.sync(Node(url=fx_server.url), fx_other_session)


@typechecked
@mark.parametrize('code', [500, 503])
def test_sync_node_unavailable_on_get_blocks(
        fx_user: User, fx_session: scoped_session,
        fx_server: WSGIServer, fx_other_session: Session,
        fx_novice_status: typing.Mapping[str, str],
        code: int
):
    move = fx_user.create_novice(fx_novice_status)
    block = Block.create(fx_user, [move])
    Block.sync(Node(url=fx_server.url), fx_other_session)
    serialized = block.serialize(
        use_bencode=False,
        include_suffix=True,
        include_moves=True,
        include_hash=True
    )
    serialized['id'] = block.id + 1
    with Mocker() as m:
        m.register_uri(
            'GET', f'{fx_server.url}/blocks/last',
            json={'block': serialized},
            status_code=200,
        )
        m.register_uri(
            'GET', f'{fx_server.url}/blocks/1',
            json={'block': serialized},
            status_code=200,
        )
        m.get(url=f'{fx_server.url}/blocks', status_code=code)
        Block.sync(Node(url=fx_server.url), fx_other_session)
        assert not fx_other_session.query(Block).get(serialized['id'])


def test_flush_session_while_syncing(fx_user, fx_session, fx_other_session,
                                     fx_novice_status):
    # 1. block validation failure scenario
    # syncing without flushing can cause block validation failure
    move = fx_user.create_novice(fx_novice_status)
    invalid_block = Block.create(fx_user, [move])
    fx_session.delete(invalid_block)

    # syncing valid blocks from another node
    new_blocks = [
        {
            "created_at": "2018-04-13 11:36:17.920869",
            "creator": "ET8ngv45qwhkDiJS1ZrUxndcGTzHxjPZDs",
            "difficulty": 0,
            "hash": "da0182c494660af0d9dd288839ceb86498708f38c800363cd46ed1730013a4d8", # noqa
            "id": 1,
            "version": 2,
            "moves": [],
            "prev_hash": None,
            "root_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", # noqa
            "suffix": "00"
        },
        {
            "created_at": "2018-04-13 11:36:17.935392",
            "creator": "ET8ngv45qwhkDiJS1ZrUxndcGTzHxjPZDs",
            "difficulty": 1,
            "hash": "014c44b9382a45c2a70d817c090e6b78af22b8f34b57fd7edb474344f25c439c", # noqa
            "id": 2,
            "version": 2,
            "moves": [],
            "prev_hash": "da0182c494660af0d9dd288839ceb86498708f38c800363cd46ed1730013a4d8", # noqa
            "root_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", # noqa
            "suffix": "0b"
        }
    ]

    def add_block(new_block):
        block = Block.deserialize(new_block)
        fx_session.add(block)
        return block

    valid_block1 = add_block(new_blocks[0])
    valid_block2 = add_block(new_blocks[1])

    assert invalid_block.hash == \
        fx_session.query(Block).get(valid_block2.id - 1).hash
    assert valid_block2.valid is False

    fx_session.query(Block).delete()

    # 2. valid scenario
    # flush session after deleting the invalid block
    move = fx_user.create_novice(fx_novice_status)
    invalid_block = Block.create(fx_user, [move])
    fx_session.delete(invalid_block)
    fx_session.flush()

    valid_block1 = add_block(new_blocks[0])
    valid_block2 = add_block(new_blocks[1])

    assert valid_block1.hash == \
        fx_session.query(Block).get(valid_block2.id - 1).hash
    assert valid_block2.valid


def test_ensure_block(fx_user: User):

    class ValidMove(Move):
        __mapper_args__ = {
            'polymorphic_identity': 'valid',
        }

    move = fx_user.move(ValidMove())
    Block.create(fx_user, [move])
    assert move.block
    assert move.block_id
    with raises(NotImplementedError):
        move.execute()


@typechecked
@mark.parametrize('value, high, expected', [
    (0, 1, 0),
    (1, 1, 1),
    (2, 1, 0),
])
def test_find_branch_point(
        fx_session: scoped_session, fx_server: WSGIServer,
        fx_user: User, value: int, high: int, expected: int
):
    node = Node(url=fx_server.url)
    Block.create(fx_user, [])
    assert find_branch_point(node, fx_session, value, high) == expected


@typechecked
@mark.parametrize('code', [500, 502, 503])
def test_find_branch_point_raise_error(fx_session: scoped_session, code: int):
    node = Node(url='http://test.neko')
    with raises(NodeUnavailable), Mocker() as m:
        m.get('http://test.neko/blocks/1', status_code=500)
        find_branch_point(node, fx_session, 1, 1)


def test_find_branch_point_404(fx_session: scoped_session):
    node = Node(url='http://test.neko')
    with Mocker() as m:
        m.get('http://test.neko/blocks/1', status_code=404)
        assert find_branch_point(node, fx_session, 1, 1) == 0
