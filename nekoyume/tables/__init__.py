import os

from dataclasses import dataclass
from pkg_resources import resource_string

from nekoyume.battle import WeightedList


class TableData(dict):
    def __init__(self, header, data):
        for i in range(len(header)):
            t = type(getattr(self, header[i]))
            setattr(self, header[i], t(data[i]))


@dataclass
class ExpData(TableData):
    id: str = ''
    exp_max: int = 0

    def __init__(self, header, data):
        super().__init__(header, data)


@dataclass
class ItemData(TableData):
    id: str = ''
    cls: str = ''
    param_0: int = 0
    param_1: int = 0
    param_2: int = 0

    def __init__(self, header, data):
        super().__init__(header, data)


@dataclass
class ItemDropData(TableData):
    id: str = ''
    zone_id: str = ''
    item_id: str = ''
    weight: int = 0

    def __init__(self, header, data):
        super().__init__(header, data)


@dataclass
class MonsterAppearData(TableData):
    id: str = ''
    zone_id: str = ''
    monster_id: str = ''
    weight: int = 0

    def __init__(self, header, data):
        super().__init__(header, data)


@dataclass
class MonsterData(TableData):
    id: str = ''
    strength: int = 0
    dexterity: int = 0
    intelligence: int = 0
    constitution: int = 0
    luck: int = 0
    defense: int = 0
    skill_0: str = ''
    skill_1: str = ''
    skill_2: str = ''
    skill_3: str = ''
    reward_exp: int = 0

    def __init__(self, header, data):
        super().__init__(header, data)


@dataclass
class SkillData(TableData):
    id: str = ''
    cls: str = ''
    cast_time: int = 0
    cooltime: int = 0
    target_count: int = 0
    power: int = 0

    def __init__(self, header, data):
        super().__init__(header, data)


@dataclass
class StatsData(TableData):
    id: str = ''
    strength: int = 0
    dexterity: int = 0
    intelligence: int = 0
    constitution: int = 0
    luck: int = 0

    def __init__(self, header, data):
        super().__init__(header, data)


@dataclass
class ZoneData(TableData):
    id: str = ''
    unlock_level: int = 0

    def __init__(self, header, data):
        super().__init__(header, data)


class Table(dict):
    separator = '\t'

    def __init__(self, filename, datacls):
        if type(filename) == str:
            self.load(filename, datacls)
        elif type(filename) == list:
            for f in filename:
                self.load(f, datacls)

    def load(self, filename, datacls):
        text = resource_string(
            'nekoyume', os.path.join('tables', filename)
        ).decode('utf-8')
        lines = text.split('\n')
        header = lines[0].split(Table.separator)
        for line in lines[1:]:
            data = line.split(Table.separator)
            self[data[0]] = datacls(header, data)

    def get(self, id):
        if type(id) is int:
            return super().get(str(id))
        return super().get(id)


class Tables:
    exp = Table('exp.tsv', ExpData)
    item_drop = Table('item_drop.tsv', ItemDropData)
    items = Table(['items.tsv', 'item_equips.tsv'], ItemData)
    monster_appear = Table('monster_appear.tsv', MonsterAppearData)
    monsters = Table('monsters.tsv', MonsterData)
    skills = Table(['skills.tsv', 'monster_skills.tsv'], SkillData)
    stats = Table('stats.tsv', StatsData)
    zone = Table('zone.tsv', ZoneData)

    @classmethod
    def get_exp_max(cls, level: int) -> int:
        try:
            return cls.exp[str(level)].exp_max
        except KeyError:
            return 0

    @classmethod
    def get_item_drop_list(cls, zone: str) -> WeightedList:
        drop_items = WeightedList()
        for id_ in Tables.item_drop:
            data = Tables.item_drop[id_]
            if data.zone_id == zone:
                drop_items.add(data.item_id, data.weight)
        return drop_items

    @classmethod
    def get_monster_appear_list(cls, zone: str) -> WeightedList:
        appear_monsters = WeightedList()
        for id_ in Tables.monster_appear:
            data = Tables.monster_appear[id_]
            if data.zone_id == zone:
                appear_monsters.add(data.monster_id, data.weight)
        return appear_monsters
