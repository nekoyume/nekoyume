import datetime
import os
from typing import Mapping, Optional
import urllib.parse

from requests import post
from requests.exceptions import ConnectionError, Timeout

from .block import Block
from .node import Node
from .orm import db


DEFAULT_BROADCAST_LIMIT = os.environ.get('BROADCAST_LIMIT', 100)


def broadcast_node(
        serialized: Mapping[str, str],
        sent_node: Optional[Node]=None,
        my_node: Optional[Node]=None,
):
    for node in db.session.query(Node):
        if sent_node and sent_node.url == node.url:
            continue
        try:
            if my_node:
                serialized['sent_node'] = my_node.url
            url = urllib.parse.urljoin(node.url, '/nodes')
            post(url, json=serialized,
                 timeout=3)
            node.last_connected_at = datetime.datetime.utcnow()
            db.session.add(node)
        except (ConnectionError, Timeout):
            continue

    db.session.commit()
    return True


def broadcast_block(
        serialized: Mapping[str, object],
        sent_node: Optional[Node]=None,
        my_node: Optional[Node]=None,
):
    """
    It broadcast this block to every nodes you know.

    :param      serialized: serialized :class:`nekoyume.block.Block`.
                            that will be broadcasted.
    :param       sent_node: sent :class:`nekoyume.node.Node`.
                            this node ignore sent node.
    :param         my_node: my :class:`nekoyume.node.Node`.
                            received node ignore my node when they
                            broadcast received object.
    """
    for node in db.session.query(Node):
        if sent_node and sent_node.url == node.url:
            continue
        try:
            if my_node:
                serialized['sent_node'] = my_node.url
            url = urllib.parse.urljoin(node.url, '/blocks')
            res = post(url, json=serialized, timeout=3)
            if res.status_code == 403:
                result = res.json()
                # 0 is Genesis block.
                block_id = result.get('block_id', 0)
                query = db.session.query(Block).filter(
                    Block.id.between(block_id, serialized['id'])
                ).order_by(Block.id)
                offset = 0
                while True:
                    sync_blocks = query[
                        offset:offset+DEFAULT_BROADCAST_LIMIT
                    ]
                    # TODO bulk api
                    for block in sync_blocks:
                        s = block.serialize(
                            use_bencode=False,
                            include_suffix=True,
                            include_moves=True,
                            include_hash=True
                        )
                        post(url, json=s, timeout=3)
                    offset += DEFAULT_BROADCAST_LIMIT
                    if len(sync_blocks) < DEFAULT_BROADCAST_LIMIT:
                        break
            node.last_connected_at = datetime.datetime.utcnow()
            db.session.add(node)
        except (ConnectionError, Timeout):
            continue
    db.session.commit()
    return True
