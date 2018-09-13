from enum import IntEnum


class CharacterType(IntEnum):
    NONE = 0
    PLAYER = 1
    MONSTER = 2


class ItemType(IntEnum):
    ITEM = 0,
    FOOD = 1,
    HEAD = 2,
    ARMOR = 3,
    WEAPON = 4,


class AttackType(IntEnum):
    MELEE = 0
    RANGED = 1
    MAGIC = 2
