from enum import IntEnum

class CharacterType(IntEnum):
    NONE = 0
    PLAYER = 1
    MONSTER = 2

class AttackType(IntEnum):
    MELEE = 0
    RANGED = 1
    MAGIC = 2
