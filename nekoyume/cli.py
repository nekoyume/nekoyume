import click

from ptpython.repl import embed

from nekoyume.models import Node, Block
from nekoyume.app import app, db


@click.group()
def cli():
    pass


@click.command()
def shell():
    app.app_context().push()
    embed(globals(), locals())


@click.command()
@click.option('--seed', default=None,
                        help='Seed node URL to connect')
def init(seed):
    print('Creating database...')
    db.create_all()
    print(f'Updating node... (seed: {seed})')
    Node.update(Node(url=seed))
    print('Syncing blocks...')
    Block.sync()


cli.add_command(init)
cli.add_command(shell)


if __name__ == '__main__':
    cli()
