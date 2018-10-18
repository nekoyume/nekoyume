from celery import Celery

from .block import Block
from .broadcast import BlockBroadcaster, MoveBroadcaster
from .move import Move
from .node import Node
from .orm import db


__all__ = (
    'block_broadcast',
    'move_broadcast',
)


celery = Celery()


@celery.task()
def move_broadcast(move_id, sent_node_url, my_node_url, session=db.session):
    move = session.query(Move).get(move_id)
    if not move:
        return
    serialized = move.serialize(
        use_bencode=False,
        include_signature=True,
        include_id=True,
    )
    MoveBroadcaster.broadcast(
        serialized=serialized,
        sent_node=Node(url=sent_node_url),
        my_node=Node(url=my_node_url)
    )


@celery.task()
def block_broadcast(block_id, sent_node_url, my_node_url, session=db.session):
    block = session.query(Block).get(block_id)
    if not block:
        return
    serialized = block.serialize(
        use_bencode=False,
        include_suffix=True,
        include_moves=True,
        include_hash=True
    )
    BlockBroadcaster.broadcast(
        serialized=serialized,
        sent_node=Node(url=sent_node_url),
        my_node=Node(url=my_node_url)
    )
