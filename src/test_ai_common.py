"""
this is a test file for ai_common functions
this test will run the actual game and check the status to determine the function validity
"""


import random
import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer
import ai_common


class TestCommonAI(ai_common.CeacarBot):
    """
    use different flag to avoid repeatedly test one function
    """
    BASE = UnitTypeId.COMMANDCENTER

    def __init__(self):
        self.test_max_worker = False
        self.test_build_refinery = False
        self.old_supply_left = None
        self.test_add_units_cap_if_needed = False
        self.old_supply_gap = None
        self.test_idle_worker_return_to_work_trigger = False
        self.test_idle_worker_return_to_work = False

    async def on_step(self, iteration):
        if iteration == 0:
            await self.chat_send("(probe)(pylon)(cannon)(cannon)(gg)")

        test_no_base_pass = False
        if not test_no_base_pass:
            if not self.no_base(self.BASE):
                test_no_base_pass = True

        first_base = self.units(self.BASE).first

        # Test max_worker
        if self.workers.amount < 18:

            if not self.test_max_worker and self.workers.amount >= 17:
                print("max_worker test pass")
                self.test_max_worker = True

            # max worker early to speed up test process
            if not self.test_max_worker:
                await self.max_worker_if_can(UnitTypeId.SCV, first_base)

        # Test build_refinery
        if self.workers.amount > 11 and self.units(UnitTypeId.REFINERY).amount < 2:
            if not self.test_build_refinery and self.units(UnitTypeId.REFINERY).amount > 0:
                print("build_refinery pass")
                self.test_build_refinery = True

            if iteration % 10 == 0:
                await self.build_refinary(REFINERY, self.BASE)
        # allocate enough worker for gas to speed up later test
        if self.units(UnitTypeId.REFINERY).ready.exists:
            await self.allocate_workers_for_gas(UnitTypeId.REFINERY)

        # # Test upgrade_all_buildings
        # if self.workers.amount > 11:
        #     print("checking building")
        #     await self.build_needed_structure(SUPPLYDEPOT, COMMANDCENTER)
        #
        #     # await self.upgrade_all_buildings()
        #
        #     if self.units(ORBITALCOMMAND).exists:
        #         self.drop_mule()
        #
        # # Test pump_force_terran
        #     self.pump_force_terran()

        # Test drop_mule
        # if self.units(ORBITALCOMMAND).exists:
        #    if energy > 50:
        #        self.drop_mule()

        # Test add_units_cap_if_needed
        if not self.test_add_units_cap_if_needed and self.supply_left <= self.supply_gap[self.game_stage]:
            if not self.test_add_units_cap_if_needed \
                    and self.old_supply_left is not None \
                    and self.supply_left != self.old_supply_left:
                print("add_units_cap_if_needed test pass")
                self.test_add_units_cap_if_needed = True

            self.old_supply_gap = self.supply_left
            await self.add_units_cap_if_needed(UnitTypeId.COMMANDCENTER)

        # Test idle_worker_return_to_work

        if self.units(UnitTypeId.SCV).idle.amount > 0:
            self.test_idle_worker_return_to_work_trigger = True
            await self.idle_worker_return_to_work()

        if self.test_idle_worker_return_to_work_trigger and not self.test_idle_worker_return_to_work:
            if self.units(UnitTypeId.SCV).idle.amount == 0:
                print("test_idle_worker_return_to_work pass")
                self.test_idle_worker_return_to_work = True


def main():
    sc2.run_game(sc2.maps.get("AbyssalReefLE"), [
        Bot(Race.Terran, TestCommonAI()),
        Computer(Race.Terran, Difficulty.Easy)
    ], realtime=False)

if __name__ == '__main__':
    main()



