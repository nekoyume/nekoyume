from components import Component, Stats
from enums import CharacterType
from rand import WeightedList
from behaviors import BehaviorTreeStatus

class Skill(Component):
    subclasses = {}
    def __init_subclass__(cls):
        super().__init_subclass__()
        Skill.subclasses[cls.__name__] = cls

    def __init__(self):
        self.name = 'Skill'
        self.cooltime = 1
        self.nexttime = 0
        self.target_count = 1

    def tick(self, simulator):
        pass

    # todo: is_dead check to filter
    def find_targets(self, targets, filter_type):
        if self.target_count <= 0:
            return []
        weightedlist = WeightedList()
        for target in targets:
            stats = target.get_component(Stats)
            if filter_type == target.get_type()\
               and not stats.is_dead():
                weightedlist.add(target, 1)
        if len(weightedlist) == 0:
            return []
        find = []
        while len(find) < self.target_count:
            find.append(weightedlist.pop())
            if len(weightedlist) == 0:
                break
        return find


class CastSkill(Skill):
    def __init__(self):
        self.state = 0
        self.cast_time = 0
        self.cast_remain = 0


class Attack(Skill):
    def __init__(self, cooltime):
        super().__init__()
        self.name = 'Attack'
        self.cooltime = cooltime

    def tick(self, simulator):
        if self.nexttime > simulator.time:
            return BehaviorTreeStatus.FAILURE
        my_stats = self.owner.get_component(Stats)
        self.nexttime = self.nexttime + my_stats.calc_atk_cooltime()
        enemy_type = CharacterType.MONSTER if self.owner.get_type() == CharacterType.PLAYER else CharacterType.PLAYER
        targets = self.find_targets(simulator.characters, enemy_type)
        for target in targets:
            target_stats = target.get_component(Stats)
            if not target_stats:
                return BehaviorTreeStatus.FAILURE
            my_stats = self.owner.get_component(Stats)
            atk = my_stats.calc_melee_atk()
            target_stats.damaged(atk)
            simulator.log(
                '[' + self.name + '] ' + self.owner.name + 
                ' -> ' + target.name + 
                ' damaged ' + str(atk) + 
                '(hp ' + str(target_stats.hp) + ')')
            if target_stats.is_dead():
                simulator.log(target.name + ' is dead..')
        return BehaviorTreeStatus.SUCCESS


class Firewall(Attack):
    def __init__(self, cooltime):
        super().__init__(cooltime)
        self.name = 'Firewall'
        self.cooltime = cooltime
        self.casttime = 5
        self.target_count = 5


class Heal(Skill):
    def __init__(self, cooltime):
        super().__init__()
        self.name = 'Heal'
        self.cooltime = cooltime

    def tick(self, simulator):
        if self.nexttime > simulator.time:
            return BehaviorTreeStatus.FAILURE
        self.nexttime = self.nexttime + self.cooltime
        my_type = self.owner.get_type()
        targets = self.find_targets(simulator.characters, my_type)
        for target in targets:
            target_stats = target.get_component(Stats)
            if not target_stats:
                return  BehaviorTreeStatus.FAILURE
            my_stats = self.owner.get_component(Stats)
            if not my_stats:
                return BehaviorTreeStatus.FAILURE
            amount = my_stats.calc_magic_atk()
            target_stats.heal(amount)
            simulator.log(
                '[' + self.name + '] ' + self.owner.name + 
                ' -> ' + target.name + 
                ' amount ' + str(amount) + 
                '(hp ' + str(target_stats.hp) + ')')
        return  BehaviorTreeStatus.SUCCESS
