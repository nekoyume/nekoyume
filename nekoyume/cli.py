import click
import time
import os

from ptpython.repl import embed
from raven import Client

from nekoyume.models import Node, Block, Move, User, get_my_public_url
from nekoyume.app import app, db


@click.group()
def cli():
    pass


@click.command()
@click.option('--private-key',
              default='test',
              help='Private key of neko')
def neko(private_key):
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


@click.command()
def shell():
    app.app_context().push()
    embed(globals(), locals())


@click.command()
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


@click.command()
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


cli.add_command(init)
cli.add_command(neko)
cli.add_command(shell)
cli.add_command(sync)


if __name__ == '__main__':
    cli()
