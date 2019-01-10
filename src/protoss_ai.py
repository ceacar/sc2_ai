"""
NOT IMPLEMENTED
"""

import random
import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer


class ProtossBot(sc2.BotAI):
    build_order_index = 0
    build_order = _NORMAL_BUILD_ORDER_TERRAN

    game_stage = "early"
    supply_gap = {"early":3, "middle":4, "late":6}

    def __init__(self):
        self.combinedActions = []

    # PROTOSS SPECIALITY
    async def build_forward_pylon(self):
        if self.units(PYLON).amount < 2:
            if self.can_afford(PYLON):
                pos = self.enemy_start_locations[0].towards(self.game_info.map_center, random.randrange(8, 15))
                await self.build(PYLON, near=pos)
