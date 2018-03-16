from app import *
app.app_context().push()

# db.drop_all(); db.create_all();

u = User('test')

move = u.create_novice({
    'strength': '15',
    'dexterity': '12',
    'constitution': '16',
    'intelligence': '9',
    'wisdom': '8',
    'charisma': '13'})
u.create_block([move])

move = u.hack_and_slash(); u.create_block([move])

move = u.sleep(); u.create_block([move])

move = u.level_up('strength'); u.create_block([move])

move = u.say('hi...'); u.create_block([move])


[a.execute()[1] for a in Move.query.all()]
