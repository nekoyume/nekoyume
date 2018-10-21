import typing
import unittest.mock

from sqlalchemy.orm.scoping import scoped_session

from nekoyume.block import Block
from nekoyume.node import Node
from nekoyume.tasks import block_broadcast, move_broadcast
from nekoyume.user import User


def test_block_broadcast(fx_session: scoped_session,
                         fx_user: User):
    block = Block.create(fx_user, [])
    fx_session.add(block)
    fx_session.commit()
    with unittest.mock.patch('nekoyume.tasks.multicast') as m:
        block_broadcast(block.id,
                        'http://localhost:5000',
                        'http://localhost:5001',
                        session=fx_session)
        serialized = block.serialize(
            use_bencode=False,
            include_suffix=True,
            include_moves=True,
            include_hash=True
        )
        assert m.called
        args = m.call_args[1]
        assert serialized == args['serialized']
        assert isinstance(args['sent_node'], Node)
        assert args['sent_node'].url == 'http://localhost:5000'
        assert isinstance(args['my_node'], Node)
        assert args['my_node'].url == 'http://localhost:5001'
        broadcast = args['broadcast']
        assert isinstance(broadcast, typing.Callable)
        assert broadcast.__name__ == 'broadcast_block'


def test_block_broadcast_no_block(fx_session: scoped_session):
    with unittest.mock.patch('nekoyume.tasks.multicast') as m:
        block_broadcast(0,
                        'http://localhost:5000',
                        'http://localhost:5001',
                        session=fx_session)
        assert not m.called


def test_move_broadcast(fx_session: scoped_session,
                        fx_user: User,
                        fx_novice_status: typing.Mapping[str, str]):
    move = fx_user.create_novice(fx_novice_status)
    fx_session.add(move)
    fx_session.commit()
    with unittest.mock.patch('nekoyume.tasks.multicast') as m:
        move_broadcast(move.id,
                       'http://localhost:5000',
                       'http://localhost:5001',
                       session=fx_session)
        serialized = move.serialize(
            use_bencode=False,
            include_signature=True,
            include_id=True,
        )
        assert m.called
        args = m.call_args[1]
        assert serialized == args['serialized']
        assert isinstance(args['sent_node'], Node)
        assert args['sent_node'].url == 'http://localhost:5000'
        assert isinstance(args['my_node'], Node)
        assert args['my_node'].url == 'http://localhost:5001'
        broadcast = args['broadcast']
        assert isinstance(broadcast, typing.Callable)
        assert broadcast.__name__ == 'broadcast_move'


def test_move_broadcast_no_move(fx_session: scoped_session):
    with unittest.mock.patch('nekoyume.tasks.multicast') as m:
        move_broadcast(0,
                       'http://localhost:5000',
                       'http://localhost:5001',
                       session=fx_session)
        assert not m.called
