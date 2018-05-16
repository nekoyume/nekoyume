import click

from nekoyume.models import Move, User
from nekoyume.app import app


@click.command()
def run():
    app.app_context().push()
    while True:
        block = User('test').create_block(
            Move.query.filter_by(block=None).limit(20).all()
        )
        if block:
            block.broadcast()
            print(block)
