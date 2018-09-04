from behaviors import BehaviorTreeBuilder
from character import Monster
from components import Stats
from enums import MonsterName
from skills import Attack
from tables import tables


# class DummyMonster(Monster):
#     def __init__(self, name):
#         super().__init__()
#         self.name = name
#         stats_dict = tables.monsters.get(MonsterName.SLIME)
#         self.add_component(Stats(1, stats_dict))
#         for skillname, param in skills:
#             self.add_component(Skill.subclasses[skillname](param))
#         builder = BehaviorTreeBuilder()
#         builder = builder.sequence(name)
#         builder = builder.condition('is_dead', lambda b: not self.get_component(Stats).is_dead())
#         builder = builder.selector('action')
#         for skillname, param in skills:
#             builder = builder.do(skillname, self.get_component(Skill.subclasses[skillname]).tick)
#         self.behavior_tree = builder.end().end().build()


class Slime(Monster):
    def __init__(self):
        super().__init__()
        self.name = 'slime'
        stats_dict = tables.monsters.get(self.name)
        self.add_component(Stats(int(stats_dict['level']), stats_dict))
        self.add_component(Attack(2))
        self.behavior_tree = BehaviorTreeBuilder()\
            .sequence('slime')\
                .condition('is_dead', lambda b: not self.get_component(Stats).is_dead())\
                .selector('action')\
                    .do('attack', self.get_component(Attack).tick)\
                .end()\
            .end()\
            .build()


class Griffin(Monster):
    def __init__(self):
        super().__init__()
        self.name = 'griffin'
        stats_dict = tables.monsters.get(self.name)
        self.add_component(Stats(int(stats_dict['level']), stats_dict))
        self.add_component(Attack(3))
        self.behavior_tree = BehaviorTreeBuilder()\
            .sequence('griffin')\
                .condition('is_dead', lambda b: not self.get_component(Stats).is_dead())\
                .selector('action')\
                    .do('attack', self.get_component(Attack).tick)\
                .end()\
            .end()\
            .build()
