import dataclasses
import os

from pkg_resources import resource_string

from ..battle import WeightedList


class TableData(dict):
    def __init__(self, header, data):
        for key in header:
            data_type = type(getattr(self, key))
            setattr(self, key, data_type(data[header.index(key)]))


@dataclasses.dataclass
class ExpData(TableData):
    id: str = ''
    exp_max: int = 0

    def __init__(self, header, data):
        super().__init__(header, data)


@dataclasses.dataclass
class ItemData(TableData):
    id: str = ''
    cls: str = ''
    param_0: int = 0
    param_1: int = 0
    param_2: int = 0

    def __init__(self, header, data):
        super().__init__(header, data)


@dataclasses.dataclass
class ItemDropData(TableData):
    id: str = ''
    zone_id: str = ''
    item_id: str = ''
    weight: int = 0

    def __init__(self, header, data):
        super().__init__(header, data)


@dataclasses.dataclass
class MonsterAppearData(TableData):
    id: str = ''
    zone_id: str = ''
    monster_id: str = ''
    weight: int = 0

    def __init__(self, header, data):
        super().__init__(header, data)


@dataclasses.dataclass
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


@dataclasses.dataclass
class NpcData(TableData):
    id: str = ''
    level: int = 0
    class_: str = '' # noqa

    def __init__(self, header, data):
        super().__init__(header, data)


@dataclasses.dataclass
class SkillData(TableData):
    id: str = ''
    cls: str = ''
    class_: str = '' # noqa
    unlock_lv: int = 0
    cast_time: int = 0
    cooltime: int = 0
    target_count: int = 0
    power: int = 0

    def __init__(self, header, data):
        super().__init__(header, data)


@dataclasses.dataclass
class StatsData(TableData):
    id: str = ''
    strength: int = 0
    dexterity: int = 0
    intelligence: int = 0
    constitution: int = 0
    luck: int = 0
    strength_lv: int = 0
    dexterity_lv: int = 0
    intelligence_lv: int = 0
    constitution_lv: int = 0
    luck_lv: int = 0

    def __init__(self, header, data):
        super().__init__(header, data)


@dataclasses.dataclass
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
            if line:
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
    npc = Table('npc.tsv', NpcData)
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

    @classmethod
    def get_npc_list(cls) -> WeightedList:
        npc_list = WeightedList()
        for id_ in Tables.npc:
            data = Tables.npc[id_]
            npc_list.add(data.id, 1)
        return npc_list
