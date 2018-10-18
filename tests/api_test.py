import json

from flask.testing import FlaskClient
from pytest import mark
from requests.exceptions import ConnectionError
from requests_mock import Mocker
from sqlalchemy.orm.scoping import scoped_session
from typeguard import typechecked

from nekoyume.block import Block
from nekoyume.node import Node
from nekoyume.user import User


def test_get_blocks(fx_test_client, fx_user):
    move = fx_user.sleep()

    rv = fx_test_client.get(f'/moves/{move.id}')
    assert rv.status == '200 OK'
    assert move.id.encode() in rv.data

    block = Block.create(fx_user, [move])

    rv = fx_test_client.get(f'/blocks')
    assert rv.status == '200 OK'
    assert block.hash.encode() in rv.data
    assert move.id.encode() in rv.data

    rv = fx_test_client.get(f'/blocks/{block.id}')
    assert rv.status == '200 OK'
    assert block.hash.encode() in rv.data
    assert move.id.encode() in rv.data

    rv = fx_test_client.get(f'/blocks/{block.hash}')
    assert rv.status == '200 OK'
    assert block.hash.encode() in rv.data

    rv = fx_test_client.get(f'/blocks/last')
    assert rv.status == '200 OK'
    assert block.hash.encode() in rv.data


@typechecked
def test_post_block_return_block_id(fx_test_client: FlaskClient,
                                    fx_user: User,
                                    fx_session: scoped_session):
    block = Block.create(fx_user, [])
    fx_session.add(block)
    fx_session.commit()
    block2 = Block.create(fx_user, [])
    des = block2.serialize(use_bencode=False,
                           include_suffix=True,
                           include_moves=True,
                           include_hash=True)
    des['id'] = 3
    resp = fx_test_client.post('/blocks', data=json.dumps(des),
                               content_type='application/json')
    assert resp.status_code == 403
    data = json.loads(resp.get_data())
    assert data['result'] == 'failed'
    assert data['message'] == "new block isn't our next block."
    assert data['block_id'] == 2


@typechecked
def test_post_node(fx_test_client: FlaskClient, fx_session: scoped_session):
    url = 'http://test.neko'
    assert not fx_session.query(Node).first()
    with Mocker() as m:
        m.get(url + '/ping', text='pong')
        res = fx_test_client.post(
            '/nodes',
            data=json.dumps({'url': url}),
            content_type='application/json'
        )
        assert res.status_code == 200
        assert json.loads(res.get_data())['result'] == 'success'
        node = fx_session.query(Node).filter(
            Node.url == url
        ).first()
        assert node
        assert node.last_connected_at


@typechecked
def test_post_node_400(fx_test_client: FlaskClient):
    res = fx_test_client.post('/nodes', data={})
    assert res.status_code == 400
    data = json.loads(res.get_data())
    assert data['result'] == 'failed'
    assert data['message'] == 'Invalid parameter.'

    url = 'http://test.neko'
    res = fx_test_client.post('/nodes', data=json.dumps({'url': url}))
    assert res.status_code == 400
    data = json.loads(res.get_data())
    assert data['result'] == 'failed'
    assert data['message'] == 'Invalid parameter.'


@typechecked
def test_post_node_connection_error(fx_test_client: FlaskClient,
                                    fx_session: scoped_session):
    url = 'http://test.neko'
    assert not fx_session.query(Node).first()
    with Mocker() as m:
        m.get(url + '/ping', exc=ConnectionError)
        res = fx_test_client.post(
            '/nodes',
            data=json.dumps({'url': url}),
            content_type='application/json'
        )
        assert res.status_code == 403
        data = json.loads(res.get_data())
        assert data['result'] == 'failed'
        assert data['message'] == f'Connection to node {url} was failed.'
        assert not fx_session.query(Node).filter(
            Node.url == url
        ).first()


@typechecked
@mark.parametrize('code', [404, 500, 503])
def test_post_node_status_not_200(fx_test_client: FlaskClient,
                                  fx_session: scoped_session,
                                  code: int):
    url = 'http://test.neko'
    assert not fx_session.query(Node).first()
    with Mocker() as m:
        m.get(url + '/ping', text='pong', status_code=code)
        res = fx_test_client.post(
            '/nodes',
            data=json.dumps({'url': url}),
            content_type='application/json'
        )
        assert res.status_code == 403
        data = json.loads(res.get_data())
        assert data['result'] == 'failed'
        assert data['message'] == f'Connection to node {url} was failed.'
        assert not fx_session.query(Node).filter(
            Node.url == url
        ).first()


def test_get_last_blocks_no_result(fx_test_client: FlaskClient):
    res = fx_test_client.get('/blocks/last')
    assert res.status_code == 404


def test_get_moves_no_result(fx_test_client: FlaskClient):
    res = fx_test_client.get('/moves/0')
    assert res.status_code == 404
