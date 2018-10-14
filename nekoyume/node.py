import datetime

from requests import get
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
