import datetime

from flask import Blueprint, jsonify, request
import requests

from tasks import block_broadcast, move_broadcast
from models import *


scan = Blueprint('scan', __name__, template_folder='templates')


@scan.route('/nodes', methods=['POST'])
def post_node():
    url = request.values.get('url')
    node = Node.query.get(url)
    if not node:
        node = Node(url=url)
        db.session.add(node)
    try:
        response = requests.get(f'{node.url}/blocks/last')
    except requests.exceptions.ConnectionError:
        return jsonify(
            result='failed',
            message=f'Connection to node {node.url} was failed.'
        ), 403
    if response.status_code == 200:
        node.last_connected_at = datetime.datetime.now()
        db.session.commit()
        return jsonify(result='success')
    else:
        return jsonify(
            result='failed',
            message=f'Connection to node {node.url} was failed.'
        ), 403


@scan.route(Node.get_blocks_endpoint, methods=['GET'])
def get_blocks():
    last_block = Block.query.order_by(Block.id.desc()).first()
    from_ = request.values.get('from', 1, type=int)
    to = request.values.get(
        'to',
        last_block.id if last_block else 0,
        type=int)
    blocks = Block.query.filter(
        Block.id >= from_,
        Block.id <= to
    ).order_by(Block.id.asc())
    return jsonify(blocks=[b.serialize(use_bencode=False,
                                       include_suffix=True,
                                       include_moves=True,
                                       include_hash=True)
                           for b in blocks])


@scan.route('/blocks/<string:block_hash>')
def get_block_by_hash(block_hash):
    block = Block.query.filter_by(hash=block_hash).first()
    if block:
        block = block.serialize(use_bencode=False,
                                include_suffix=True,
                                include_moves=True,
                                include_hash=True)
    return jsonify(block=block)


@scan.route('/blocks/<int:block_id>')
def get_block_by_id(block_id):
    block = Block.query.get(block_id)
    if block:
        block = block.serialize(use_bencode=False,
                                include_suffix=True,
                                include_moves=True,
                                include_hash=True)
    return jsonify(block=block)


@scan.route('/blocks/last')
def get_last_block():
    block = Block.query.order_by(Block.id.desc()).first()
    if block:
        block = block.serialize(use_bencode=False,
                                include_suffix=True,
                                include_moves=True,
                                include_hash=True)
    return jsonify(block=block)


@scan.route(Node.post_block_endpoint, methods=['POST'])
def post_block():
    new_block = request.get_json()
    last_block = Block.query.order_by(Block.id.desc()).first()

    if not last_block:
        Block.sync(
            Node.query.order_by(
                Node.last_connected_at.desc()).first())
        return jsonify(result='failed',
                       message="new block isn't our next block."), 403

    if (new_block['id'] != last_block.id + 1 or
       new_block['prev_hash'] != last_block.hash):
        if new_block['id'] > last_block.id + 1:
            Block.sync(
                Node.query.order_by(
                    Node.last_connected_at.desc()).first())
        return jsonify(result='failed',
                       message="new block isn't our next block."), 403

    block = Block()
    block.id = new_block['id']
    block.creator = new_block['creator']
    block.created_at = datetime.datetime.strptime(
        new_block['created_at'], '%Y-%m-%d %H:%M:%S.%f')
    block.prev_hash = new_block['prev_hash']
    block.hash = new_block['hash']
    block.difficulty = new_block['difficulty']
    block.suffix = new_block['suffix']
    block.root_hash = new_block['root_hash']

    for new_move in new_block['moves']:
        move = Move.query.get(new_move['id'])
        if not move:
            move = Move(
                id=new_move['id'],
                user=new_move['user'],
                name=new_move['name'],
                signature=new_move['signature'],
                tax=new_move['tax'],
                details=new_move['details'],
                created_at= datetime.datetime.strptime(
                    new_move['created_at'], '%Y-%m-%d %H:%M:%S.%f'),
                block_id=block.id,
            )
        if not move.valid:
            return jsonify(result='failed',
                           message=f"move {move.id} isn't valid."), 400
        block.moves.append(move)

    if not block.valid:
        return jsonify(result='failed',
                       message="new block isn't valid."), 400


    db.session.add(block)
    db.session.commit()
    sent_node = Node()
    if 'sent_node' in new_block:
        sent_node.url = new_block['sent_node']
    block_broadcast.delay(
        block.id,
        sent_node_url=sent_node.url,
        my_node_url=f'{request.scheme}://{request.host}'
    )
    return jsonify(result='success')


@scan.route(Node.post_move_endpoint, methods=['POST'])
def post_move():
    new_move = request.get_json()
    move = Move.query.get(new_move['id'])

    if move:
        return jsonify(result='success')

    if not move:
        move = Move(
            id=new_move['id'],
            user=new_move['user'],
            name=new_move['name'],
            signature=new_move['signature'],
            tax=new_move['tax'],
            details=new_move['details'],
            created_at= datetime.datetime.strptime(
                new_move['created_at'], '%Y-%m-%d %H:%M:%S.%f'),
        )

    if not move.valid:
        return jsonify(result='failed',
                       message=f"move {move.id} isn't valid."), 400

    db.session.add(move)
    db.session.commit()

    sent_node = Node()
    if 'sent_node' in new_move:
        sent_node.url=new_move['sent_node']

    move_broadcast.delay(
        move.id,
        sent_node_url=sent_node.url,
        my_node_url=f'{request.scheme}://{request.host}'
    )
    return jsonify(result='success')
