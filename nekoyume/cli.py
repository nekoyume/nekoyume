import click
import time

from ptpython.repl import embed

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
    while True:
        Block.sync()
        block = User(private_key).create_block(
            Move.query.filter_by(block=None).limit(20).all(),
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
def init(seed):
    click.echo('Creating database...')
    db.create_all()
    click.echo(f'Updating node... (seed: {seed})')
    Node.update(Node(url=seed))
    click.echo('Syncing blocks...')
    Block.sync(click=click)


@click.command()
def sync():
    public_url = get_my_public_url()
    if public_url:
        click.echo(f"You have a public node url. ({public_url})")
        Node.broadcast(Node.post_node_endpoint, {'url': public_url})
    while True:
        try:
            prev_id = Block.query.order_by(Block.id.desc()).first().id
        except AttributeError:
            click.echo("You need to initialize. try `nekoyume init`.")
            break
        if not prev_id:
            click.echo("You need to initialize. try `nekoyume init`.")
            break
        Block.sync(click=click)
        if prev_id == Block.query.order_by(Block.id.desc()).first().id:
            click.echo("The blockchain is up to date.")
            time.sleep(15)


cli.add_command(init)
cli.add_command(neko)
cli.add_command(shell)
cli.add_command(sync)


if __name__ == '__main__':
    cli()
