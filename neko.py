from app import *
app.app_context().push()


while True:
    block = User('test').create_block(Move.query.filter_by(block=None))
    print(block)
