import random
import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer
import ai_common
from sc2.position import Point2,Point3
import asyncio


class TerranBot(ai_common.BotCommon):
    def __init__(self):
        super().__init__()
        self.combinedActions = []
        self._NORMAL_BUILD_ORDER_TERRAN=[
            (SUPPLYDEPOT,1),
            (BARRACKS,1),
            (FACTORY,1),
            (STARPORT,1),
            (ENGINEERINGBAY,1),
            (ARMORY,1)
        ]
        self.build_order_index = 0
        self.build_order = self._NORMAL_BUILD_ORDER_TERRAN
        self.SUPPLY_DEPOT_TYPE = UnitTypeId.SUPPLYDEPOT

        self.game_stage = "early"
        self.supply_gap = {"early":3, "middle":4, "late":6}
        self.unit_count_limit_per_base = {
            UnitTypeId.SCV: 18,
            UnitTypeId.REFINERY: 2,
        }
    # def move_building_to(self, building_unit: 'a real unit like self.townhalls.first') -> 'bool':
    #     self.combinedActions.append(building_unit(AbilityId.LIFT))
    #
    #     retreatPoints = self.neighbors8(building_unit.position, distance=2) | self.neighbors8(building_unit.position, distance=4)
    #     # filter points that are pathable
    #     retreatPoints = {x for x in retreatPoints if self.in_pathing_grid(x)}
    #     print("retr points:", retreatPoints)
    #     first_retreat_point = retreatPoints.pop()
    #     if retreatPoints:
    #         self.combinedActions.append(building_unit.move(first_retreat_point))
    #
    #     if building_unit.position == first_retreat_point:
    #         self.combinedActions.append(building_unit(AbilityId.LAND))
    #         return True

    # self.combinedActions.append(building_unit.move(position))
    # self.combinedActions.append(building_unit.move(position))

    async def relocate_building_for_addon(self, building_type:'UnitTypeId.BARRACKS', flying_building_type:'UnitTypeId.BARRACKSFLYING'):
        for unit in self.units(building_type).ready:
            if unit.add_on_tag == 0:
                await self.do(unit(AbilityId.LIFT))

        for unit in self.units(flying_building_type).ready:
            await self.do(unit(AbilityId.LAND, unit.add_on_land_position))
            await asyncio.sleep(5)


    # only terran has building addon
    async def build_addon(self, building_name: 'STARPORT', addon_name:'UnitTypeId.STARPORTTECHLAB'):
        for building_unit in self.units(building_name):
            # only build addon when building can build addon and no addon is in construction
            if building_unit.add_on_tag == 0 and self.already_pending(addon_name) == 0:
                self.combinedActions.append(building_unit.build(addon_name))

    async def upgrade_building(self, building:'UnitTypeId.BARRACKS', ability:'AbilityId.BUILD_TECHLAB'):
        if self.units(building).ready.exists:
            for unit in self.units(building):
                await self.upgrade_ability(unit, ability)

    async def upgrade_orbital_command_center(self):
        if self.units(UnitTypeId.BARRACKS).ready.exists:
            self.upgrade_building(UnitTypeId.COMMANDCENTER, AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)

    async def upgrade_barrack_techlab(self):
        if self.units(UnitTypeId.BARRACKS).ready.exists:
            self.upgrade_building(UnitTypeId.BARRACKS, AbilityId.BUILD_TECHLAB_BARRACKS)

    async def upgrade_factory_techlab(self):
        if self.units(UnitTypeId.FACTORY).ready.exists:
            await self.upgrade_ability(UnitTypeId.FACTORY, AbilityId.BUILD_TECHLAB_FACTORY)

    async def upgrade_starport_techlab(self):
        if self.units(UnitTypeId.FACTORY).ready.exists:
            await self.upgrade_ability(UnitTypeId.STARPORT, AbilityId.BUILD_TECHLAB_STARPORT)

    async def upgrade_all_buildings(self):
        self.upgrade_orbital_command_center()
        self.upgrade_barrack_techlab()
        self.upgrade_factory_techlab()
        self.upgrade_starport_techlab()

    def produce_force(self, building: 'UnitTypeId.BARRACKS', unit: 'UnitTypeId.MARINE', batch_count=1, maintain_at=999):
        if self.units(unit).amount >= maintain_at:
            # maintain unit at a level
            return
        counter = 0
        for producer in self.units(building):
            if self.can_afford(unit) and producer.noqueue:
                print("producing", unit, "from", building)
                self.combinedActions.append(producer.train(unit))
                # await self.do(producer.train(unit))
                counter = counter + 1
            if counter >= batch_count:
                # has queued targeted number
                break

    def pump_force_terran(self):
        # set a ceiling for unit count to avoid any single unit produced too much
        tank_count_max = max(2, self.units(UnitTypeId.MARINE).amount/4)
        marine_count_max = max(6, self.units(UnitTypeId.SIEGETANK).amount*4)
        viking_count_max = self.units(UnitTypeId.SIEGETANK).amount/2
        medivac_count_max = self.units(UnitTypeId.MARINE).amount/5
        if self.units(UnitTypeId.BARRACKSTECHLAB).ready.exists:
            self.produce_force(UnitTypeId.BARRACKS, UnitTypeId.MARINE, batch_count=1,
                               maintain_at=marine_count_max)
        if self.units(UnitTypeId.FACTORYTECHLAB).ready.exists:
            self.produce_force(UnitTypeId.FACTORY, UnitTypeId.SIEGETANK, batch_count=1, maintain_at=tank_count_max)
        if self.units(UnitTypeId.STARPORTREACTOR).ready.exists:
            self.produce_force(UnitTypeId.STARPORT, UnitTypeId.MEDIVAC, batch_count=1, maintain_at=medivac_count_max)
            self.produce_force(UnitTypeId.STARPORT, UnitTypeId.VIKINGSKY_UNIT, batch_count=1,
                               maintain_at=viking_count_max)

    def drop_mule(self):
        # manage orbital energy and drop mules
        for oc in self.units(UnitTypeId.ORBITALCOMMAND).filter(lambda x: x.energy >= 50):
            mfs = self.state.mineral_field.closer_than(10, oc)
            if mfs:
                mf = max(mfs, key=lambda x: x.mineral_contents)
                self.combinedActions.append(oc(AbilityId.CALLDOWNMULE_CALLDOWNMULE, mf))

    def morph_commandcenter(self):
        if self.units(UnitTypeId.BARRACKS).ready.exists \
                and self.can_afford(UnitTypeId.ORBITALCOMMAND)\
                and self.units(UnitTypeId.COMMANDCENTER).ready.exists:
            for cc in self.units(UnitTypeId.COMMANDCENTER).idle:
                self.combinedActions.append(cc(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND))

    def get_base_count(self):
        command_center_count = self.units(UnitTypeId.COMMANDCENTER).amount
        orbital_command_count = self.units(UnitTypeId.ORBITALCOMMAND).amount
        planetary_fortress_count = self.units(UnitTypeId.PLANETARYFORTRESS).amount
        return command_center_count + orbital_command_count + planetary_fortress_count

    def get_first_base(self) -> 'a real unit like self.townhalls.first':
        # Terran COMMANDCENTER will morph into ORBITALCOMMAND
        unit = None
        if self.units(UnitTypeId.COMMANDCENTER).exists:
            unit = self.units(UnitTypeId.COMMANDCENTER).first
        elif self.units(UnitTypeId.ORBITALCOMMAND).exists:
            unit = self.units(UnitTypeId.ORBITALCOMMAND).first
        elif self.units(UnitTypeId.PLANETARYFORTRESS).exists:
            unit = self.units(UnitTypeId.PLANETARYFORTRESS).first
        else:
            print("no base located")
        return unit

    def get_first_base_type(self) ->'UnitTypeId.ORBITALCOMMAND':
        # Terran COMMANDCENTER will morph into ORBITALCOMMAND
        if self.units(UnitTypeId.COMMANDCENTER).exists:
            unit_name = UnitTypeId.COMMANDCENTER
        elif self.units(UnitTypeId.ORBITALCOMMAND).exists:
            unit_name = UnitTypeId.ORBITALCOMMAND
        else:
            unit_name = UnitTypeId.PLANETARYFORTRESS
        return unit_name

    def can_do_first_attack(self):
        #print("tank count {0}, marine count {1}".format(self.units(UnitTypeId.SIEGETANK).ready.amount,\
        #                                                self.units(UnitTypeId.MARINE).ready.amount))

        if self.units(UnitTypeId.SIEGETANK).ready.amount > 2 and self.units(UnitTypeId.MARINE).ready.amount > 6:
            print("can attack now")
            return True
        else:
            return False

    def get_unit_upper_limit(self, unit_type: 'UnitTypeId.SCV'):
        return self.unit_count_limit_per_base[unit_type] * (self.units(UnitTypeId.COMMANDCENTER).amount
                                                            + self.units(UnitTypeId.ORBITALCOMMAND).amount
                                                            + self.units(UnitTypeId.PLANETARYFORTRESS).amount)

    def get_attack_force(self):
        units = []
        for unit_type in [UnitTypeId.MARINE, UnitTypeId.SIEGETANK,
                          UnitTypeId.VIKING, UnitTypeId.MEDIVAC, UnitTypeId.THOR]:
            units = units + self.units(unit_type).ready
        # print("attack team selected:", units)
        return units

    def lower_supply_depot(self):
        for depot in self.units(UnitTypeId.SUPPLYDEPOT).ready:
            self.combinedActions.append(depot(AbilityId.MORPH_SUPPLYDEPOT_LOWER))

    def get_supply_depot_count(self):
        # overwrite the get_supply_depot_count method since terran has three types of supply depot
        return self.units(UnitTypeId.SUPPLYDEPOT).amount + self.units(UnitTypeId.SUPPLYDEPOTLOWERED).amount + self.units(UnitTypeId.SUPPLYDEPOTDROP).amount
        + self.already_pending(UnitTypeId.SUPPLYDEPOT).amount + self.already_pending(UnitTypeId.SUPPLYDEPOTLOWERED).amount + self.already_pending(UnitTypeId.SUPPLYDEPOTDROP).amount
