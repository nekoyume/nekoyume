import math

from .....tables import Tables
from .... import WeightedList
from ....enums import AttackType, CharacterType, ItemType
from ....status.skills import Attack as StatusAttack
from ....status.skills import Casting
from ....status.skills import Heal as StatusHeal
from ....status.skills import Taunt as StatusTaunt
from ....status.stats import Dead, GetExp
from ...bag import Bag
from ...stats import MonsterStats, Stats
from .. import Behavior, BehaviorTreeStatus
from ..aggro import Aggro


class Skill(Behavior):
    subclasses = {}

    def __init_subclass__(cls):
        super().__init_subclass__()
        Skill.subclasses[cls.__name__] = cls

    def __init__(self, name):
        self.name = name
        self.data = Tables.skills[name]
        self.nexttime = self.data.cooltime
        self.is_casting = False
        self.cast_remains = 0

    def tick(self, simulator):
        pass

    def find_targets(self, simulator, filter_type):
        if not self.data.target_count:
            return []
        weightedlist = WeightedList()
        for target in simulator.characters:
            stats = target.get_component(Stats)
            aggro = target.get_component(Aggro)
            if filter_type == target.type_\
               and not stats.is_dead():
                weightedlist.add(target, aggro.value)
        if len(weightedlist) == 0:
            return []
        targets = []
        while len(targets) < self.data.target_count:
            targets.append(weightedlist.pop(simulator.random))
            if len(weightedlist) == 0:
                break
        return targets

    def calc_atk(self):
        my_stats = self.owner.get_component(Stats)
        my_bag = self.owner.get_component(Bag)
        weapon = my_bag.get_equipped(ItemType.WEAPON)
        atk = 0
        if weapon:
            atk = weapon.get_atk()
            if weapon.atk_type == AttackType.MELEE:
                atk += my_stats.calc_melee_atk()
            elif weapon.atk_type == AttackType.RANGED:
                atk += my_stats.calc_ranged_atk()
            elif weapon.atk_type == AttackType.MAGIC:
                atk += my_stats.calc_magic_atk()
        else:
            atk += my_stats.calc_melee_atk()
        atk = math.floor(atk * (self.data.power * 0.01))
        return atk

    def is_cooltime(self, simulator):
        return self.nexttime > simulator.time

    def kill(self, simulator, target):
        simulator.logger.log(Dead(id_=target.id_))
        if self.owner.type_ is CharacterType.PLAYER:
            for character in simulator.characters:
                if character.type_ is CharacterType.PLAYER:
                    stats = character.get_component(Stats)
                    monster_stats = target.get_component(MonsterStats)
                    stats.get_exp(monster_stats.data.reward_exp)
                    simulator.logger.log(GetExp(
                        exp=monster_stats.data.reward_exp))

    def casting(self, simulator):
        if self.cast_remains > 0:
            self.cast_remains -= 1
            simulator.logger.log(Casting(
                id_=self.owner.id_,
                tick_remain=self.cast_remains,
            ))
            return True
        if not self.is_casting and self.data.cast_time > 0:
            self.is_casting = True
            self.cast_remains = self.data.cast_time
            simulator.logger.log(Casting(
                id_=self.owner.id_,
                tick_remain=self.cast_remains,
            ))
            return True
        self.is_casting = False
        return False


class Attack(Skill):
    """Weapon-based attack."""
    def tick(self, simulator):
        if self.is_cooltime(simulator):
            return BehaviorTreeStatus.FAILURE
        my_stats = self.owner.get_component(Stats)
        self.nexttime += my_stats.calc_cooltime(self.data.cooltime)
        atk = self.calc_atk()
        target_type = my_stats.get_target_type()
        targets = self.find_targets(simulator, target_type)
        for index, target in enumerate(targets):
            target_stats = target.get_component(Stats)
            damaged = target_stats.damaged(atk)
            target_aggro = target.get_component(Aggro)
            target_aggro.add(self.owner.id_, 1)
            simulator.logger.log(StatusAttack(
                id_=self.owner.id_,
                time=simulator.time,
                name=self.data.id,
                value=damaged,
                target_id=target.id_,
                target_hp=target_stats.hp,
                target_remain=len(targets) - index - 1,
            ))
            if target_stats.is_dead():
                self.kill(simulator, target)
        return BehaviorTreeStatus.SUCCESS


class Spell(Skill):
    def tick(self, simulator):
        if self.is_cooltime(simulator):
            return BehaviorTreeStatus.FAILURE
        if self.casting(simulator):
            return BehaviorTreeStatus.SUCCESS
        my_aggro = self.owner.get_component(Aggro)
        my_aggro.value += 1
        my_stats = self.owner.get_component(Stats)
        self.nexttime += my_stats.calc_cooltime(self.data.cooltime)
        atk = math.floor(my_stats.calc_magic_atk() * (self.data.power * 0.01))
        target_type = my_stats.get_target_type()
        targets = self.find_targets(simulator, target_type)
        for index, target in enumerate(targets):
            target_stats = target.get_component(Stats)
            damaged = target_stats.damaged(atk)
            target_aggro = target.get_component(Aggro)
            target_aggro.add(self.owner.id_, 1)

            simulator.logger.log(StatusAttack(
                id_=self.owner.id_,
                time=simulator.time,
                name=self.data.id,
                value=damaged,
                target_id=target.id_,
                target_hp=target_stats.hp,
                target_remain=len(targets) - index - 1,
            ))
            if target_stats.is_dead():
                self.kill(simulator, target)
        return BehaviorTreeStatus.SUCCESS


class Heal(Skill):
    def tick(self, simulator):
        if self.is_cooltime(simulator):
            return BehaviorTreeStatus.FAILURE
        if self.casting(simulator):
            return BehaviorTreeStatus.SUCCESS
        my_aggro = self.owner.get_component(Aggro)
        my_aggro.value += 1
        my_stats = self.owner.get_component(Stats)
        self.nexttime += my_stats.calc_cooltime(self.data.cooltime)
        targets = self.find_targets(simulator, self.owner.type_)
        for index, target in enumerate(targets):
            target_stats = target.get_component(Stats)
            if target_stats:
                amount = math.floor(
                    my_stats.calc_magic_atk() * (self.data.power * 0.01))
                target_stats.heal(amount)
                simulator.logger.log(StatusHeal(
                    id_=self.owner.id_,
                    time=simulator.time,
                    name=self.data.id,
                    value=amount,
                    target_id=target.id_,
                    target_hp=target_stats.hp,
                    target_remain=len(targets) - index - 1,
                ))
        return BehaviorTreeStatus.SUCCESS


class Slow(Skill):
    def tick(self, simulator):
        # TODO
        return BehaviorTreeStatus.FAILURE


class Taunt(Skill):
    def tick(self, simulator):
        if self.is_cooltime(simulator):
            return BehaviorTreeStatus.FAILURE
        my_aggro = self.owner.get_component(Aggro)
        my_aggro.value += math.floor(self.data.power * 0.01)
        my_stats = self.owner.get_component(Stats)
        self.nexttime += my_stats.calc_cooltime(self.data.cooltime)
        simulator.logger.log(StatusTaunt(id_=self.owner.id_))
        return BehaviorTreeStatus.SUCCESS
