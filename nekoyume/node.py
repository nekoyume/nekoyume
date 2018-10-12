import datetime
import typing

from requests import get, post
from requests.exceptions import ConnectionError, Timeout
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.session import Session

from .orm import db


class Node(db.Model):
    """This object contains node information you know."""

    #: URL of node
    url = db.Column(db.String, primary_key=True)
    #: last connected datetime of the node
    last_connected_at = db.Column(db.DateTime, nullable=False, index=True)

    get_nodes_endpoint = '/nodes'
    get_blocks_endpoint = '/blocks'

    @classmethod
    def get(cls, url: str, session: Session=db.session):
        get_node = Node.query.filter_by(url=url).first
        node = get_node()
        if node:
            return node
        elif get(f'{url}/ping').text == 'pong':
            node = Node(url=url, last_connected_at=datetime.datetime.utcnow())
            if session:
                session.add(node)
                try:
                    session.commit()
                except IntegrityError:
                    node = get_node()
                    if node is None:
                        raise
                    return node
            return node
        else:
            return None

    @classmethod
    def update(cls, node: 'Node'):
        """
        Update recent node list by scrapping other nodes' information.
        """
        try:
            response = get(f"{node.url}{Node.get_nodes_endpoint}")
        except (ConnectionError, Timeout):
            return
        for url in response.json()['nodes']:
            try:
                Node.get(url)
            except (ConnectionError, Timeout):
                continue
        db.session.commit()

    def ping(self):
        try:
            result = get(f'{self.url}/ping').text == 'pong'
            if result:
                self.last_connected_at = datetime.datetime.utcnow()
            return result
        except (ConnectionError, Timeout):
            return False

    @classmethod
    def broadcast(cls,
                  endpoint: str,
                  serialized_obj: typing.Mapping[str, object],
                  sent_node: typing.Optional['Node']=None,
                  my_node: typing.Optional['Node']=None,
                  session: Session=db.session) -> bool:
        """
        It broadcast `serialized_obj` to every nodes you know.

        :param        endpoint: endpoint of node to broadcast
        :param  serialized_obj: object that will be broadcasted.
        :param       sent_node: sent :class:`nekoyume.node.Node`.
                                this node ignore sent node.
        :param         my_node: my :class:`nekoyume.node.Node`.
                                received node ignore my node when they
                                broadcast received object.
        """

        for node in session.query(cls):
            if sent_node and sent_node.url == node.url:
                continue
            try:
                if my_node:
                    serialized_obj['sent_node'] = my_node.url
                post(node.url + endpoint, json=serialized_obj,
                     timeout=3)
                node.last_connected_at = datetime.datetime.utcnow()
                session.add(node)
            except (ConnectionError, Timeout):
                continue

        session.commit()
        return True
