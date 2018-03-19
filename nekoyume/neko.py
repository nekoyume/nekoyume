import click

from nekoyume.models import Move, User
from nekoyume.app import app


@click.command()
def run():
    app.app_context().push()
    while True:
        block = User('test').create_block(Move.query.filter_by(block=None))
        block.broadcast()
        print(block)
