from nekoyume.battle.components import ComponentContainer
from nekoyume.battle.components.bag import Bag
from nekoyume.battle.components.behaviors import BehaviorTreeBuilder
from nekoyume.battle.components.behaviors.aggro import Aggro
from nekoyume.battle.components.behaviors.skills import Skill
from nekoyume.battle.components.stats import Stats, PlayerStats, MonsterStats
from nekoyume.battle.enums import CharacterType
from nekoyume.battle.tables import Tables


class Character(ComponentContainer):
    def __init__(self):
        super().__init__()
        self.name = 'Character'
        self.type_ = CharacterType.NONE
        self.class_ = ''
        self.behavior_tree = None

    def tick(self, simulator):
        if self.behavior_tree:
            self.behavior_tree.tick(simulator)

    def to_dict(self):
        stats = self.get_component(Stats)
        dict_ = {
            'id': self.name,
            'hp': stats.hp,
        }
        return dict_

    def to_avatar(self, avatar, hp_max=False):
        stats = self.get_component(PlayerStats)
        avatar.level = stats.level
        avatar.exp_max = stats.exp_max
        avatar.exp = stats.exp
        avatar.hp_max = stats.calc_hp_max()
        avatar.hp = avatar.hp_max if hp_max else stats.hp
        avatar.strength = stats.data.strength
        avatar.dexterity = stats.data.dexterity
        avatar.intelligence = stats.data.intelligence
        avatar.constitution = stats.data.constitution
        avatar.luck = stats.data.luck
        bag = self.get_component(Bag)
        avatar.items = bag.items


class Factory:
    character_id = 0

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
        character.behavior_tree = b.build()

    @classmethod
    def create_player(cls, name, class_, level, skills, items):
        Factory.character_id += 1
        character = Character()
        character.id_ = Factory.character_id
        character.type_ = CharacterType.PLAYER
        character.name = name
        character.class_ = class_
        character.add_component(PlayerStats(class_, level, 0, 0))
        stats = character.get_component(Stats)
        stats.hp = stats.calc_hp_max()
        character.add_component(Bag(items))
        character.add_component(Aggro())
        Factory.set_behavior(character, skills)
        return character

    @classmethod
    def create_from_avatar(cls, avatar, details):
        Factory.character_id += 1
        character = Character()
        character.id_ = Factory.character_id
        character.type_ = CharacterType.PLAYER
        character.name = avatar.name
        character.class_ = avatar.class_
        character.add_component(
            PlayerStats(avatar.class_, avatar.level, avatar.hp, avatar.exp))
        bag = Bag(avatar.items)
        if 'weapon' in details:
            bag.equip(int(details['weapon']))
        if 'armor' in details:
            bag.equip(int(details['armor']))
        character.add_component(bag)
        character.add_component(Aggro())
        Factory.set_behavior(character, ['attack'])
        return character

    @classmethod
    def create_monster(cls, name):
        Factory.character_id += 1
        data = Tables.monsters[name]
        character = Character()
        character.id_ = Factory.character_id
        character.type_ = CharacterType.MONSTER
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
