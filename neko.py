from models import Move, User
from app import app


app.app_context().push()


while True:
    block = User('test').create_block(Move.query.filter_by(block=None))
    block.broadcast()
    print(block)
