import os
import time

from babel.messages.frontend import compile_catalog
from click import IntRange, ParamType, argument, echo, group, option
from coincurve import PrivateKey
from ptpython.repl import embed
from raven import Client

from nekoyume.app import app, db
from nekoyume.models import Block, Move, Node, User, get_my_public_url


DEFAULT_SEED_NODE_URL = os.environ.get(
    'SEED_NODE_URL',
    'http://seed.nekoyu.me'
)


class PrivateKeyType(ParamType):
    name = 'private key'

    def convert(self, value, param, ctx) -> PrivateKey:
        val = value[2:] if value.startswith(('0x', '0X')) else value
        try:
            num = bytes.fromhex(val)
            return PrivateKey(num)
        except (ValueError, TypeError):
            self.fail('%s is not a valid private key of 64 hexadecimal digits')


@group()
def cli():
    pass


@cli.command()
@argument('private_key', type=PrivateKeyType())
def neko(private_key: PrivateKey):
    app.app_context().push()
    Client(os.environ.get('SENTRY_DSN'))

    while True:
        Block.sync()
        block = User(private_key).create_block(
            [m
             for m in Move.query.filter_by(block=None).limit(20).all()
             if m.valid],
            echo=echo,
        )
        if block:
            block.broadcast()
            echo(block)


@cli.command()
def shell():
    app.app_context().push()
    embed(globals(), locals())


@cli.command()
@option('--seed',
        default=DEFAULT_SEED_NODE_URL,
        help='Seed node URL to connect')
@option('--sync/--skip-sync',
        default=False,
        help='Synchronize after initialization or skip it')
def init(seed, sync):
    echo('Creating database...')
    db.create_all()
    echo(f'Updating node... (seed: {seed})')
    if sync:
        Node.update(Node.get(url=seed))
        echo('Syncing blocks...')
        Block.sync(echo=echo)

    echo('Compiling translations...')
    dir_path = os.path.abspath(os.path.dirname(__file__))
    compile_command = compile_catalog()
    compile_command.directory = dir_path + '/translations'
    compile_command.finalize_options()
    compile_command.run()


@cli.command()
@option('--seed',
        default=DEFAULT_SEED_NODE_URL,
        help='Seed node URL to connect')
def sync(seed: str):
    Client(os.environ.get('SENTRY_DSN'))
    public_url = get_my_public_url()
    if public_url:
        echo(f"You have a public node url. ({public_url})")
        Node.broadcast(Node.post_node_endpoint, {'url': public_url})
    Node.update(Node.get(url=seed))
    engine = db.engine
    if not engine.dialect.has_table(engine.connect(), Block.__tablename__):
        echo("You need to initialize. try `nekoyume init`.")
        return False
    while True:
        try:
            prev_id = Block.query.order_by(Block.id.desc()).first().id
        except AttributeError:
            prev_id = 0
        Block.sync(echo=echo)
        try:
            if prev_id == Block.query.order_by(Block.id.desc()).first().id:
                echo("The blockchain is up to date.")
                time.sleep(15)
        except AttributeError:
            echo(("There is no well-connected node. "
                  "please check you network."))
            break


@cli.command()
def doctor():
    id = 1
    for block in Block.query.order_by(Block.id.asc()):
        if block.id != id:
            echo(f'Block {id}: is empty.')
            id = block.id
        if not block.valid:
            echo(f'Block {id}: is invalid.')
        id += 1


@cli.command()
def repair():
    id = 1
    for block in Block.query.order_by(Block.id.asc()):
        if block.id != id or not block.valid:
            Block.query.filter(Block.id >= block.id).delete(
                synchronize_session='fetch'
            )
            echo(f'Block {id}+ was removed.')
            break
        id += 1

    deleted_move_ids = []
    for move in Move.query:
        if not move.valid:
            move.delete()
            deleted_move_ids.append(move.id)

    if deleted_move_ids:
        echo(f'Following moves were removed.')
        for deleted_move_id in deleted_move_ids:
            echo(f'   {deleted_move_id}')

    db.session.commit()


@cli.command()
@option('--host',
        default='127.0.0.1',
        help='Host to listen')
@option('--port',
        type=IntRange(0, 65535),
        metavar='PORT',
        default=5000,
        help='Port number to listen')
def dev(host: str, port: int) -> None:
    app.run(debug=True, host=host, port=port)


if __name__ == '__main__':
    cli()
