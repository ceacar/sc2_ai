import random
import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer
import terran_ai


class GrazeEin(terran_ai.TerranBot):
    """
    use different flag to avoid repeatedly test one function
    """

    def __init__(self):
        super().__init__()
        self.old_supply_left = None
        self.old_supply_gap = None
        self.combinedActions = []

        #self._NORMAL_BUILD_ORDER_TERRAN=[
        #    (SUPPLYDEPOT,1),
        #    (BARRACKS,1),
        #    (FACTORY,1),
        #    (STARPORT,1),
        #    (ENGINEERINGBAY,1),
        #    (ARMORY,1)
        #]

        #self.game_stage = "early"
        #self.suppy_gap = {"early":3, "middle":4, "late":6}

    async def on_step(self, iteration):
        self.combinedActions = []

        if iteration == 0:
            await self.chat_send("(probe)(pylon)(cannon)(cannon)(gg)")

        first_base = self.get_first_base()
        if self.workers.amount <= self.get_unit_upper_limit(UnitTypeId.SCV):
            self.max_worker_if_can(UnitTypeId.SCV, first_base)

        if self.workers.amount > 14\
                and self.units(UnitTypeId.REFINERY).amount < self.get_unit_upper_limit(UnitTypeId.REFINERY):

            if iteration % 10 == 0:
                await self.build_refinary(UnitTypeId.REFINERY, self.get_first_base_type())

        if self.units(UnitTypeId.ORBITALCOMMAND).exists:
            self.drop_mule()

        # building depot if supply is needed, give iteration gap to avoid building a depot too many times
        if iteration % 12 == 0 and self.supply_left <= 5:
            await self.add_units_cap_if_needed(UnitTypeId.SUPPLYDEPOT)

        if iteration % 5 == 0:
            #saturate gas faster than normal distribute_workers
            self.allocate_workers_for_gas(UnitTypeId.REFINERY)

        if iteration % 10 == 0:
            # takes care of idle scv
            await self.distribute_workers()

        await self.build_needed_structure(UnitTypeId.SUPPLYDEPOT,
                                              UnitTypeId.COMMANDCENTER)

        if iteration % 15 == 0:
            self.determine_building_list()

        # barrack adding TECHLAB addon
        if iteration % 30 == 0:
            await self.relocate_building_for_addon(UnitTypeId.BARRACKS, UnitTypeId.BARRACKSFLYING)
            await self.relocate_building_for_addon(UnitTypeId.FACTORY, UnitTypeId.FACTORYFLYING)
            await self.relocate_building_for_addon(UnitTypeId.STARPORT, UnitTypeId.STARPORTFLYING)

        if self.units(UnitTypeId.BARRACKS).ready.exists:
            await self.build_addon(UnitTypeId.BARRACKS, UnitTypeId.BARRACKSTECHLAB)
        if self.units(UnitTypeId.FACTORY).ready.exists:
            await self.build_addon(UnitTypeId.FACTORY, UnitTypeId.FACTORYTECHLAB)
        if self.units(UnitTypeId.STARPORT).ready.exists:
            await self.build_addon(UnitTypeId.STARPORT, UnitTypeId.STARPORTTECHLAB)

        # morph_commandcenter
        self.morph_commandcenter()

        if self.units(UnitTypeId.SCV).amount >= 18:
            await self.expand_base_accordingly()

        self.pump_force_terran()

        if self.can_do_first_attack():
            units = self.get_attack_force()
            self.move_to_enemy_location(units)
            self.attack_enemy(units)

        self.tank_siege_ai()

        if iteration % 35 == 0:
            units = self.get_attack_force()
            self.defend_base(units)

        # lower supply depot to avoid possibility of unit locked in a tight space
        if iteration % 30 == 0:
            self.lower_supply_depot()

        await self.do_actions(self.combinedActions)


def main():
    sc2.run_game(sc2.maps.get("AbyssalReefLE"), [
        Bot(Race.Terran, GrazeEin()),
        Computer(Race.Terran, Difficulty.Medium)
    ], realtime=False)

    #play as human
    #Human(Race.Terran),
    #Bot(Race.Zerg, ZergRushBot())

if __name__ == '__main__':
    main()



