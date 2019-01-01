import random
import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer
import ai_common


class TerranAI(ai_common.CeacarBot):
    BASE = COMMANDCENTER
    async def on_step(self, iteration):
        if iteration == 0:
            await self.chat_send("(probe)(pylon)(cannon)(cannon)(gg)")
        print("checking no base issue")
        if self.no_base(self.BASE):
            await self.worker_suicide_attack()
            return

        first_base = self.units(self.BASE).first

        print("checking worker max issue")
        await self.max_worker_if_can(SCV, first_base)
        if self.workers.amount > 9:
            print("checking refinary")
            await self.build_refinary(REFINERY,self.BASE)

        if self.workers.amount > 11:
            print("checking building")
            await self.build_needed_structure(SUPPLYDEPOT, COMMANDCENTER)

            # await self.upgrade_all_buildings()

            if self.units(ORBITALCOMMAND).exists:
                self.drop_mule()

            self.pump_force_terran()
        # if self.units(ORBITALCOMMAND).exists:
        #    if energy > 50:
        #        self.drop_mule()

        await self.idle_worker_return_to_work()
        await self.add_units_cap_if_needed(self.BASE)

def main():
    sc2.run_game(sc2.maps.get("AbyssalReefLE"), [
        Bot(Race.Terran, TerranAI()),
        Computer(Race.Terran, Difficulty.Easy)
    ], realtime=False)

if __name__ == '__main__':
    main()

