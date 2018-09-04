from behaviors import BehaviorTreeBuilder
from character import Player
from components import Stats
from component.buff import Buff
from enums import ClassType
from skills import Skill, Attack, Firewall, Heal
from tables import tables


class DummyPlayer(Player):
    def __init__(self, name, class_type, skills):
        super().__init__()
        self.name = name
        self.class_ = class_type
        stats_dict = tables.stats.get(name)
        self.add_component(Stats(1, stats_dict))
        for skillname, param in skills:
            self.add_component(Skill.subclasses[skillname](param))
        builder = BehaviorTreeBuilder()
        builder = builder.sequence(name)
        builder = builder.condition('is_dead', lambda b: not self.get_component(Stats).is_dead())
        builder = builder.selector('action')
        for skillname, param in skills:
            builder = builder.do(skillname, self.get_component(Skill.subclasses[skillname]).tick)
        self.behavior_tree = builder.end().end().build()


class Warrior(Player):
    def __init__(self):
        super().__init__()
        self.name = 'swordman'
        self.class_ = ClassType.SWORDMAN
        stats_dict = tables.stats.get(self.name)
        self.add_component(Stats(1, stats_dict))
        #self.add_component(Attack(2))
        self.add_component(Skill.subclasses['Attack'](2))
        self.behavior_tree = BehaviorTreeBuilder()\
            .sequence('warrior')\
                .condition('is_dead', lambda b: not self.get_component(Stats).is_dead())\
                .selector('action')\
                    .do('attack', self.get_component(Attack).tick)\
                .end()\
            .end()\
            .build()


class Mage(Player):
    def __init__(self):
        super().__init__()
        self.name = 'mage'
        self.class_ = ClassType.MAGE
        stats_dict = tables.stats.get(self.name)
        self.add_component(Stats(1, stats_dict))
        self.add_component(Attack(5))
        self.add_component(Firewall(8))
        self.behavior_tree = BehaviorTreeBuilder()\
            .sequence('mage')\
                .condition('is_dead', lambda b: not self.get_component(Stats).is_dead())\
                .selector('action')\
                    .do('firewall', self.get_component(Firewall).tick)\
                    .do('attack', self.get_component(Attack).tick)\
                .end()\
            .end()\
            .build()


class Monk(Player):
    def __init__(self):
        super().__init__()
        self.name = 'mage'
        self.class_ = ClassType.MAGE
        stats_dict = tables.stats.get(self.name)
        self.add_component(Stats(1, stats_dict))
        self.add_component(Heal(3))
        self.behavior_tree = BehaviorTreeBuilder()\
            .sequence('monk')\
                .condition('is_dead', lambda b: not self.get_component(Stats).is_dead())\
                .selector('action')\
                    .do('heal', self.get_component(Heal).tick)\
                .end()\
            .end()\
            .build()
