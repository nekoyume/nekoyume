from enum import IntEnum

class CharacterType(IntEnum):
    NONE = 0
    PLAYER = 1
    MONSTER = 2

class ClassType(IntEnum):
    NOVICE = 0
    SWORDMAN = 1
    MAGE = 2
    ARCHER = 3

class MonsterName(IntEnum):
    SLIME = 0
    GRIFFIN = 1
