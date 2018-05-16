import click
import time

from ptpython.repl import embed

from nekoyume.models import Node, Block, Move, User
from nekoyume.app import app, db


@click.group()
def cli():
    pass


@click.command()
def shell():
    app.app_context().push()
    embed(globals(), locals())


@click.command()
@click.option('--seed',
              default=None,
              help='Seed node URL to connect')
def init(seed):
    print('Creating database...')
    db.create_all()
    print(f'Updating node... (seed: {seed})')
    Node.update(Node(url=seed))
    print('Syncing blocks...')
    Block.sync()


@click.command()
def sync():
    while True:
        prev_id = Block.query.order_by(Block.id.desc()).first().id
        if not prev_id:
            print("You need to initialize. try `nekoyume init`.")
            break
        Block.sync()
        if prev_id == Block.query.order_by(Block.id.desc()).first().id:
            print("The blockchain is up to date.")
            time.sleep(15)


cli.add_command(init)
cli.add_command(shell)
cli.add_command(sync)


if __name__ == '__main__':
    cli()
