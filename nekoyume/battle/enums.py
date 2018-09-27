import enum


class CharacterType(enum.IntEnum):
    NONE = 0
    PLAYER = 1
    MONSTER = 2


class ItemType(enum.IntEnum):
    ITEM = 0,
    FOOD = 1,
    HEAD = 2,
    ARMOR = 3,
    WEAPON = 4,


class AttackType(enum.IntEnum):
    MELEE = 0
    RANGED = 1
    MAGIC = 2
