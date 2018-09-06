from behaviors import BehaviorTreeBuilder
from components import ComponentContainer, Stats
from enums import CharacterType
from skills import Skill
from tables import Tables


class Character(ComponentContainer):
    def __init__(self):
        super().__init__()
        self.name = 'Character'
        self.type_ = CharacterType.NONE
        self.class_ = ''
        self.group = 0
        self.behavior_tree = None

    def tick(self, simulator):
        if self.behavior_tree:
            self.behavior_tree.tick(simulator)

    def set_skills(self, skills):
        for skillname in skills:
            self.add_component(Skill.subclasses[skillname]())
        builder = BehaviorTreeBuilder()
        builder = builder.sequence(self.name)
        builder = builder.condition('is_dead', lambda b: not self.get_component(Stats).is_dead())
        builder = builder.selector('action')
        for skillname in skills:
            builder = builder.do(skillname, self.get_component(Skill.subclasses[skillname]).tick)
        self.behavior_tree = builder.end().end().build()


class Player(Character):
    def __init__(self, name, level, class_, skills):
        super().__init__()
        self.name = name
        self.type_ = CharacterType.PLAYER
        self.class_ = class_
        self.group = 1
        self.add_component(Stats(level, Tables.stats[class_]))
        self.set_skills(skills)


class Monster(Character):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.type_ = CharacterType.MONSTER
        self.group = 2
        data = Tables.monsters[name]
        self.add_component(Stats(1, data))
        skills = data['skills'].split(',')
        self.set_skills(skills)
        