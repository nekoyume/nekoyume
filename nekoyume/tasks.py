from celery import Celery

from nekoyume.models import Block, Move, Node


celery = Celery()


@celery.task()
def move_broadcast(move_id, sent_node_url, my_node_url):
    try:
        Move.query.get(move_id).broadcast(Node(url=sent_node_url),
                                          Node(url=my_node_url))
    except AttributeError:
        pass


@celery.task()
def block_broadcast(block_id, sent_node_url, my_node_url):
    try:
        Block.query.get(block_id).broadcast(Node(url=sent_node_url),
                                            Node(url=my_node_url))
    except AttributeError:
        pass
