from behaviors import BehaviorTreeBuilder
from components.aggro import Aggro
from components.bag import Bag
from components.component import ComponentContainer
from components.stats import Stats
from enums import CharacterType
from skills import Skill
from tables import Tables


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


class Factory:
    character_id = 0
    @classmethod
    def set_behavior(cls, character, skills):
        b = BehaviorTreeBuilder()
        b = b.sequence(character.name)
        b = b.condition('is_dead', lambda b: not character.get_component(Stats).is_dead())
        #b = b.selector('concentration')
        #b = b.condition('is_concentration', lambda b: not character.test())
        #b = b.end()
        b = b.selector('action')
        for skillname in skills:
            data = Tables.skills[skillname]
            skillcls = data['cls']
            character.add_component(Skill.subclasses[skillcls](skillname))
            b = b.do(skillname, character.get_component(Skill.subclasses[skillcls]).tick)
        b = b.end()
        b = b.do('aggro', character.get_component(Aggro).tick)
        b = b.end()
        character.behavior_tree = b.build()

    @classmethod
    def create_player(cls, name, level, class_, skills, items):
        Factory.character_id += 1
        character = Character()
        character.id_ = Factory.character_id
        character.type_ = CharacterType.PLAYER
        character.name = name
        character.class_ = class_
        character.add_component(Stats(level, Tables.stats[class_]))
        character.add_component(Bag(items))
        character.add_component(Aggro())
        Factory.set_behavior(character, skills)
        return character

    @classmethod
    def create_monster(cls, name):
        Factory.character_id += 1
        data = Tables.monsters[name]
        character = Character()
        character.id_ = Factory.character_id
        character.type_ = CharacterType.MONSTER
        character.name = name
        character.add_component(Stats(1, data))
        character.add_component(Bag())
        character.add_component(Aggro())
        skills = []
        for i in range(4):
            s = 'skill_' + str(i)
            if data[s]:
                skills.append(data[s])
        Factory.set_behavior(character, skills)
        return character
        