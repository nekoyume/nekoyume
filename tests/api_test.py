import json

from flask.testing import FlaskClient
from sqlalchemy.orm.session import Session

from nekoyume.models import Block, User


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


def test_post_block_return_block_id(fx_test_client: FlaskClient,
                                    fx_user: User,
                                    fx_session: Session):
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
