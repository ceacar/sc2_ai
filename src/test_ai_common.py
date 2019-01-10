"""
this is a test file for ai_common functions
this test will run the actual game and check the status to determine the function validity
"""


import random
import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer
import terran_ai


class TestTerranAI(terran_ai.TerranBot):
    """
    use different flag to avoid repeatedly test one function
    """

    def __init__(self):
        super().__init__()
        self.test_pump_force_terran = False
        self.test_move_building_to = False
        self.test_drop_mule = False
        self.test_max_worker = False
        self.test_build_refinery = False
        self.old_supply_left = None
        self.test_add_units_cap_if_needed = False
        self.old_supply_gap = None
        self.test_idle_worker_return_to_work_trigger = False
        self.test_idle_worker_return_to_work = False
        self.test_build_needed_structure = False
        self.test_build_addon = False
        self.test_morph_commandcenter = False
        self.combinedActions = []
        self.test_expand_base = False

        #self._NORMAL_BUILD_ORDER_TERRAN=[
        #    (SUPPLYDEPOT,1),
        #    (BARRACKS,1),
        #    (FACTORY,1),
        #    (STARPORT,1),
        #    (ENGINEERINGBAY,1),
        #    (ARMORY,1)
        #]
        #self.build_order_index = 0
        #self.build_order = self._NORMAL_BUILD_ORDER_TERRAN
        #self.BASE = UnitTypeId.COMMANDCENTER
        #self.game_stage = "early"
        #self.suppy_gap = {"early":3, "middle":4, "late":6}

    async def on_step(self, iteration):
        self.combinedActions = []

        if iteration == 0:
            await self.chat_send("(probe)(pylon)(cannon)(cannon)(gg)")

        test_no_base_pass = False
        if not test_no_base_pass:
            if not self.no_base(self.get_first_base_type()):
                test_no_base_pass = True

        first_base = self.get_first_base()

        # Test max_worker
        if self.workers.amount < 18:
            if not self.test_max_worker and self.workers.amount >= 17:
                print("max_worker test pass")
                self.test_max_worker = True
            # max worker early to speed up test process
            if not self.test_max_worker:
                self.max_worker_if_can(UnitTypeId.SCV, first_base)
                # await self.max_worker_if_can(UnitTypeId.SCV, first_base)

        # Test build_refinery
        if self.workers.amount > 11 and self.units(UnitTypeId.REFINERY).amount < 2:
            if not self.test_build_refinery and self.units(UnitTypeId.REFINERY).amount > 0:
                print("build_refinery pass")
                self.test_build_refinery = True

            if iteration % 10 == 0:
                await self.build_refinary(REFINERY, self.get_first_base_type())
        # allocate enough worker for gas to speed up later test
        if self.units(UnitTypeId.REFINERY).ready.exists:
            self.allocate_workers_for_gas(UnitTypeId.REFINERY)

        # Test drop_mule
        if not self.test_drop_mule:
                self.drop_mule()

        if not self.test_drop_mule and self.units(UnitTypeId.MULE).exists:
            self.test_drop_mule = True

        # Test add_units_cap_if_needed
        if not self.test_add_units_cap_if_needed and self.supply_left <= self.supply_gap[self.game_stage]:
            if not self.test_add_units_cap_if_needed \
                    and self.old_supply_left is not None \
                    and self.supply_left != self.old_supply_left:
                print("add_units_cap_if_needed test pass")
                self.test_add_units_cap_if_needed = True

            self.old_supply_gap = self.supply_left
            await self.add_units_cap_if_needed(UnitTypeId.SUPPLYDEPOT)

        # Test idle_worker_return_to_work
        if iteration % 10 == 0:
            if self.units(UnitTypeId.SCV).idle.amount > 0:
                self.test_idle_worker_return_to_work_trigger = True
                self.idle_worker_return_to_work()

        if self.test_idle_worker_return_to_work_trigger and not self.test_idle_worker_return_to_work:
            if self.units(UnitTypeId.SCV).idle.amount == 0:
                print("test_idle_worker_return_to_work pass")
                self.test_idle_worker_return_to_work = True

        # Test build_needed_structure
        if not self.test_build_needed_structure:
            await self.build_needed_structure(UnitTypeId.SUPPLYDEPOT,
                                              UnitTypeId.COMMANDCENTER)

        if not self.test_build_needed_structure \
                and self.units(UnitTypeId.BARRACKS).ready.exists \
                and self.units(UnitTypeId.STARPORT).ready.exists \
                and self.units(UnitTypeId.ENGINEERINGBAY).ready.exists \
                and self.units(UnitTypeId.ARMORY).ready.exists:
            print("test_build_needed_structure passed")
            self.test_build_needed_structure = True

        # Test barrack adding TECHLAB addon
        if not self.test_build_addon:
            if self.units(UnitTypeId.BARRACKS).ready.exists:
                print("building BARRACKS TECHLAB")
                await self.build_addon(UnitTypeId.BARRACKS, UnitTypeId.BARRACKSTECHLAB)

        # if not self.test_build_addon:
            if self.units(UnitTypeId.BARRACKSTECHLAB).ready.exists:
                print("test_build_addon passed")
                self.test_build_addon = True

        # test morph_commandcenter
        if not self.test_morph_commandcenter:
            self.morph_commandcenter()

        if self.already_pending(UnitTypeId.ORBITALCOMMAND):
            self.test_morph_commandcenter = True
            print("test_morph_commandcenter passed")

        # Test expand_base
        if not self.test_expand_base:
            await self.expand_base(UnitTypeId.COMMANDCENTER)
        if not self.test_expand_base and self.townhalls.amount > 1:
            print("test_expand_base success")
            self.test_expand_base = True

        # Test move terran building
        # if not self.test_move_building_to and self.units(UnitTypeId.BARRACKSTECHLAB).ready.exists:
        #     first_bak = self.units(UnitTypeId.BARRACKS).first
        #     self.move_building_to(first_bak, self.townhalls.first.position)

        # Test moving factory and then land
        # if self.units(UnitTypeId.FACTORY).ready.exists:
        #     fac = self.units(UnitTypeId.FACTORY).ready.first
        #     if fac:
        #         await self.do(fac(AbilityId.LIFT))
        #         print("try moving to landing point:", fac.add_on_land_position)
        #         # await self.do(fac(AbilityId.MOVE, fac.add_on_land_position))
        #         await self.do(fac(AbilityId.LAND, fac.add_on_land_position))

        if not self.test_pump_force_terran:
            self.pump_force_terran()
        if not self.test_pump_force_terran:
            if self.units(UnitTypeId.MARINE).amount > 0:
                print("test_pump_force_terran passed")
                self.test_pump_force_terran = True

        await self.do_actions(self.combinedActions)


def main():
    sc2.run_game(sc2.maps.get("AbyssalReefLE"), [
        Bot(Race.Terran, TestTerranAI()),
        Computer(Race.Terran, Difficulty.Easy)
    ], realtime=False)

if __name__ == '__main__':
    main()



