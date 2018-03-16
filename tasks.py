from celery import Celery

from models import *


celery = Celery()


@celery.task()
def move_broadcast(move_id, sent_node_url, my_node_url):
    Move.query.get(move_id).broadcast(Node(url=sent_node_url),
                                      Node(url=my_node_url))


@celery.task()
def block_broadcast(block_id, sent_node_url, my_node_url):
    Block.query.get(block_id).broadcast(Node(url=sent_node_url),
                                        Node(url=my_node_url))
