import click
import time
import os

from babel.messages.frontend import compile_catalog
from ptpython.repl import embed
from raven import Client
from coincurve import PrivateKey

from nekoyume.models import Node, Block, Move, User, get_my_public_url
from nekoyume.app import app, db


class PrivateKeyType(click.ParamType):
    name = 'private key'

    def convert(self, value, param, ctx) -> PrivateKey:
        val = value[2:] if value.startswith(('0x', '0X')) else value
        try:
            num = bytes.fromhex(val)
            return PrivateKey(num)
        except (ValueError, TypeError):
            self.fail('%s is not a valid private key of 64 hexadecimal digits')


@click.group()
def cli():
    pass


@cli.command()
@click.argument('private_key', type=PrivateKeyType())
def neko(private_key: PrivateKey):
    app.app_context().push()
    Client(os.environ.get('SENTRY_DSN'))

    while True:
        Block.sync()
        block = User(private_key).create_block(
            [m
             for m in Move.query.filter_by(block=None).limit(20).all()
             if m.valid],
            click=click,
        )
        if block:
            block.broadcast()
            click.echo(block)


@cli.command()
def shell():
    app.app_context().push()
    embed(globals(), locals())


@cli.command()
@click.option('--seed',
              default=None,
              help='Seed node URL to connect')
@click.option('--sync/--skip-sync',
              default=False,
              help='Synchronize after initialization or skip it')
def init(seed, sync):
    click.echo('Creating database...')
    db.create_all()
    click.echo(f'Updating node... (seed: {seed})')
    if seed:
        Node.update(Node.get(url=seed))
    else:
        Node.update()
    if sync:
        click.echo('Syncing blocks...')
        Block.sync(click=click)

    click.echo('Compiling translations...')
    compile_command = compile_catalog()
    compile_command.directory = 'nekoyume/translations'
    compile_command.finalize_options()
    compile_command.run()


@cli.command()
def sync():
    Client(os.environ.get('SENTRY_DSN'))
    public_url = get_my_public_url()
    if public_url:
        click.echo(f"You have a public node url. ({public_url})")
        Node.broadcast(Node.post_node_endpoint, {'url': public_url})
    Node.update()
    engine = db.engine
    if not engine.dialect.has_table(engine.connect(), Block.__tablename__):
        click.echo("You need to initialize. try `nekoyume init`.")
        return False
    while True:
        try:
            prev_id = Block.query.order_by(Block.id.desc()).first().id
        except AttributeError:
            prev_id = 0
        Block.sync(click=click)
        try:
            if prev_id == Block.query.order_by(Block.id.desc()).first().id:
                click.echo("The blockchain is up to date.")
                time.sleep(15)
        except AttributeError:
            click.echo(("There is no well-connected node. "
                        "please check you network."))
            break


@cli.command()
def doctor():
    id = 1
    for block in Block.query.order_by(Block.id.asc()):
        if block.id != id:
            click.echo(f'Block {id}: is empty.')
            id = block.id
        if not block.valid:
            click.echo(f'Block {id}: is invalid.')
        id += 1


@cli.command()
def repair():
    id = 1
    for block in Block.query.order_by(Block.id.asc()):
        if block.id != id or not block.valid:
            Block.query.filter(Block.id >= block.id).delete(
                synchronize_session='fetch'
            )
            click.echo(f'Block {id}+ was removed.')
            break
        id += 1

    deleted_move_ids = []
    for move in Move.query:
        if not move.valid:
            move.delete()
            deleted_move_ids.append(move.id)

    if deleted_move_ids:
        click.echo(f'Following moves were removed.')
        for deleted_move_id in deleted_move_ids:
            click.echo(f'   {deleted_move_id}')

    db.session.commit()


@cli.command()
@click.option('--host',
              default='127.0.0.1',
              help='Host to listen')
@click.option('--port',
              type=click.IntRange(0, 65535),
              metavar='PORT',
              default=5000,
              help='Port number to listen')
def dev(host: str, port: int) -> None:
    app.run(debug=True, host=host, port=port)


if __name__ == '__main__':
    cli()
