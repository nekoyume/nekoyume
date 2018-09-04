from components import ComponentContainer
from enums import CharacterType, ClassType
from rand import WeightedList


class Character(ComponentContainer):
    def __init__(self):
        super().__init__()
        self.name = 'Character'
        self.type_ = CharacterType.NONE
        self.group = 0
        self.behavior_tree = None

    def tick(self, simulator):
        if self.behavior_tree:
            self.behavior_tree.tick(simulator)
    
    def get_type(self):
        return self.type_


class Player(Character):
    def __init__(self):
        super().__init__()
        self.name = 'Player'
        self.class_ = ClassType.NOVICE
        self.type_ = CharacterType.PLAYER
        self.group = 1


class Monster(Character):
    def __init__(self):
        super().__init__()
        self.name = 'Monster'
        self.type_ = CharacterType.MONSTER
        self.group = 2
        