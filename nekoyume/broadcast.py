import datetime
from typing import Mapping, Optional
import urllib.parse

from requests import post
from requests.exceptions import ConnectionError, Timeout

from .node import Node
from .orm import db


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
