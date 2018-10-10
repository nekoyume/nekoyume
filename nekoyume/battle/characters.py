from ..tables import Tables
from .components import ComponentContainer
from .components.bag import Bag
from .components.behaviors import BehaviorTreeBuilder
from .components.behaviors.aggro import Aggro
from .components.behaviors.skills import Skill
from .components.stats import MonsterStats, PlayerStats, Stats
from .enums import CharacterType


class Character(ComponentContainer):
    def __init__(self):
        super().__init__()
        self.id_ = 0
        self.type_ = CharacterType.NONE
        self.class_ = ''
        self.name = 'Character'
        self.behavior = None

    def tick(self, simulator):
        if self.behavior:
            self.behavior.tick(simulator)

    def to_dict(self):
        stats = self.get_component(Stats)
        dict_ = {
            'id': self.name,
            'hp': stats.hp,
        }
        return dict_

    def to_avatar(self, avatar, hp_recover=False):
        stats = self.get_component(PlayerStats)
        avatar.level = stats.level
        avatar.strength = stats.strength
        avatar.dexterity = stats.dexterity
        avatar.intelligence = stats.intelligence
        avatar.constitution = stats.constitution
        avatar.luck = stats.luck
        avatar.exp_max = stats.exp_max
        avatar.exp = stats.exp
        avatar.hp_max = stats.calc_hp_max()
        avatar.hp = avatar.hp_max if hp_recover else stats.hp
        bag = self.get_component(Bag)
        avatar.items = bag.items

    def get_skills(self):
        stats = self.get_component(Stats)
        skills = []
        for (k, v) in Tables.skills.items():
            if v.class_ == self.class_ or v.class_ == '':
                if v.unlock_lv <= stats.level:
                    skills.append(k)
        skills.reverse()
        return skills


class Factory:
    def __init__(self):
        self.character_id = 0

    @classmethod
    def set_behavior(cls, character, skills):
        b = BehaviorTreeBuilder()
        b = b.sequence(character.name)
        b = b.condition(
            'is_dead',
            lambda b: not character.get_component(Stats).is_dead())
        b = b.selector('action')
        for skillname in skills:
            data = Tables.skills[skillname]
            skillcls = data.cls
            character.add_component(Skill.subclasses[skillcls](skillname))
            b = b.do(
                skillname,
                character.get_component(Skill.subclasses[skillcls]).tick)
        b = b.end()
        b = b.do('aggro', character.get_component(Aggro).tick)
        b = b.end()
        character.behavior = b.build()

    def create_player(self, name, class_, level, items):
        self.character_id += 1
        character = Character()
        character.id_ = self.character_id
        character.type_ = CharacterType.PLAYER
        character.class_ = class_
        character.name = name
        character.add_component(PlayerStats(class_, level, 0, 0))
        stats = character.get_component(Stats)
        stats.hp = stats.calc_hp_max()
        character.add_component(Bag(items))
        character.add_component(Aggro())
        skills = character.get_skills()
        Factory.set_behavior(character, skills)
        return character

    def create_from_avatar(self, avatar, details):
        self.character_id += 1
        character = Character()
        character.id_ = self.character_id
        character.type_ = CharacterType.PLAYER
        character.class_ = avatar.class_
        character.name = avatar.name
        character.add_component(
            PlayerStats(avatar.class_, avatar.level, avatar.hp, avatar.exp))
        bag = Bag(avatar.items)
        if 'weapon' in details:
            bag.equip(int(details['weapon']))
        if 'armor' in details:
            bag.equip(int(details['armor']))
        character.add_component(bag)
        character.add_component(Aggro())
        skills = character.get_skills()
        Factory.set_behavior(character, skills)
        return character

    def create_npc(self, id):
        self.character_id += 1
        data = Tables.npc[id]
        character = Character()
        character.id_ = self.character_id
        character.type_ = CharacterType.PLAYER
        character.class_ = data.class_
        character.name = id
        character.add_component(PlayerStats(data.class_, data.level, 0, 0))
        stats = character.get_component(Stats)
        stats.hp = stats.calc_hp_max()
        character.add_component(Bag())
        character.add_component(Aggro())
        skills = character.get_skills()
        Factory.set_behavior(character, skills)
        return character

    def create_monster(self, name):
        self.character_id += 1
        data = Tables.monsters[name]
        character = Character()
        character.id_ = self.character_id
        character.type_ = CharacterType.MONSTER
        character.class_ = name
        character.name = name
        character.add_component(MonsterStats(name))
        character.add_component(Bag())
        character.add_component(Aggro())
        skills = []
        for i in range(4):
            s = 'skill_' + str(i)
            skillcls = getattr(data, s, '')
            if skillcls:
                skills.append(skillcls)
        Factory.set_behavior(character, skills)
        return character
