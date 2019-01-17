import random
from enum import Enum
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
        ]

        #Mech Build
        self._MECH_BUILD_ORDER=[
            (ENGINEERINGBAY,1),
            (ARMORY,1),
            (FACTORY,4),
            (STARPORT,4),
        ]

        self._LATE_MECH_BUILD_ORDER=[
            (ENGINEERINGBAY,1),
            (ARMORY,2),
            (FACTORY,6),
            (STARPORT,6),
        ]
        self.build_order_index = 0
        self.build_order = self._NORMAL_BUILD_ORDER_TERRAN
        self.SUPPLY_DEPOT_TYPE = UnitTypeId.SUPPLYDEPOT

        self.Stages = Enum('Stages', 'early middle late')
        self.game_stage = self.Stages.early
        self.supply_gap = {self.Stages.early: 3, self.Stages.middle: 4, self.Stages.late: 6}
        self.unit_count_limit_per_base = {
            UnitTypeId.SCV: 18,
            UnitTypeId.REFINERY: 2,
        }
        self.expand_base_dict = {
            self.Stages.early: 2,
            self.Stages.middle: 3,
            self.Stages.late: 5,
        }
        self.last_stage = None

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

    def set_building_order(self):
        if self.last_stage != self.game_stage:
            if self.game_stage == self.Stages.early:
                print("early stage building order selected")
                self.build_order = self._NORMAL_BUILD_ORDER_TERRAN

            if self.game_stage == self.Stages.middle and self.minerals > 500:
                print("middle stage building order selected")
                self.build_order = self._MECH_BUILD_ORDER

            if self.game_stage == self.Stages.late:
                print("latestage building order selected")
                self.build_order = self._LATE_MECH_BUILD_ORDER

            print("build order changed to:", self.build_order, self.build_order_index)
            self.last_stage = self.game_stage
            self.build_order_index = 0

    def game_stage_research(self):
        # AI needs to check on game stage, and this game_stage will affect build order and units
        print("self.supply_cap",self.supply_cap)
        print("self.supply_gap",self.supply_gap)
        print(self.supply_left)
        print(self.game_stage)
        if self.supply_cap > 50:
            print("changed to ", self.game_stage)
            self.game_stage = self.Stages.middle
        if self.supply_cap > 90:
            print("changed to ", self.game_stage)
            self.game_stage = self.Stages.late

    def determine_building_list(self):
        # building list will change accroding to game stage
        self.game_stage_research()
        self.set_building_order()

    def determine_expand_base_max(self):
        print("self.game_stage:", self.game_stage)
        return self.expand_base_dict[self.game_stage]

    def tank_siege_ai(self):
        for tank in self.units(UnitTypeId.SIEGETANK).ready:
            enemy_ground_units = self.nearest_ground_enemy(tank, 14)
            if enemy_ground_units.exists:
                print("sieging tank:", tank)
                tank(AbilityId.SIEGEBREAKERSIEGE_SIEGEMODE)
                tank(AbilityId.SIEGEMODE_SIEGEMODE)
                tank(AbilityId.SIEGEBREAKERUNSIEGE_UNSIEGE)
                tank(AbilityId.UNSIEGE_UNSIEGE)
            else:
                enemy_ground_units = self.nearest_ground_enemy(tank, 40)
                if enemy_ground_units:
                    # tank moves in when enemy too far away
                    print("enemy too far away form {0}, moving in".format(tank))
                    tank.attack(random.choice(enemy_ground_units))

        for tank in self.units(UnitTypeId.SIEGETANKSIEGED):
            enemy_ground_units = self.nearest_ground_enemy(tank, 14)
            # tank will unsiege when no enemy insight
            if not enemy_ground_units.exists:
                print("sieged tank: no enemy insight, unsiege;",tank)
                tank(AbilityId.UNSIEGE_UNSIEGE)
            else:
                # picks a middle range enemy to attack, so tank can maximize the splash damage
                enemy_in_max_dps_position = enemy_ground_units[len(enemy_ground_units)/2]
                print("siege tank firing at ", enemy_in_max_dps_position)
                self.combinedActions.append(tank.attack(enemy_in_max_dps_position))

    async def expand_base_accordingly(self):
        expand_base_max_count = self.determine_expand_base_max()
        await self.expand_base(UnitTypeId.COMMANDCENTER, expand_max=expand_base_max_count)

    async def relocate_building_for_addon(self, building_type: 'UnitTypeId.BARRACKS',
                                          flying_building_type: 'UnitTypeId.BARRACKSFLYING'):
        for unit in self.units(building_type).ready:
            # print(unit, "has_add_on", unit.has_add_on)
            #if unit.add_on_tag == 0:
            if unit.has_add_on:
                # print("lifing", unit, "add_on_tag:", unit.add_on_tag)
                # print(building_type, self.units(building_type).amount)
                # print("bak, factory, startport techlab count:",
                #       self.units(UnitTypeId.BARRACKSTECHLAB).amount,
                #       self.units(UnitTypeId.STARPORTTECHLAB).amount,
                #       self.units(UnitTypeId.FACTORYTECHLAB).amount)
                await self.do(unit(AbilityId.LIFT))

        for unit in self.units(flying_building_type).ready:

            while True:
                landing_position = random.choice(list(self.neighbors8(unit.position, distance=3)))
                print("landing", unit, "at", landing_position)
                action_error = await self.do(unit(AbilityId.LAND, landing_position))
                print("landing result", action_error)
                if not action_error:
                    break

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
                # print("producing", unit, "from", building)
                self.combinedActions.append(producer.train(unit))
                # await self.do(producer.train(unit))
                counter = counter + 1
            else:
                print(producer, "cannot produce", unit)
            if counter >= batch_count:
                # has queued targeted number
                break

    def produce_tank_marine_medivac(self):
        # set a ceiling for unit count to avoid any single unit produced too much
        tank_count_max = max(10, self.units(UnitTypeId.MARINE).amount/4)
        marine_count_max = max(6, self.units(UnitTypeId.SIEGETANK).amount*4)
        viking_count_max = self.units(UnitTypeId.SIEGETANK).amount/2
        medivac_count_max = self.units(UnitTypeId.MARINE).amount/5
        # print("marine tank medivac viking conut max is :", marine_count_max,
        #       tank_count_max, medivac_count_max, viking_count_max)
        if self.units(UnitTypeId.BARRACKSTECHLAB).ready.exists:
            self.produce_force(UnitTypeId.BARRACKS, UnitTypeId.MARINE, batch_count=1,
                               maintain_at=marine_count_max)
        if self.units(UnitTypeId.FACTORYTECHLAB).ready.exists:
            self.produce_force(UnitTypeId.FACTORY, UnitTypeId.SIEGETANK, batch_count=1, maintain_at=tank_count_max)
        if self.units(UnitTypeId.STARPORTTECHLAB).ready.exists:
            self.produce_force(UnitTypeId.STARPORT, UnitTypeId.MEDIVAC, batch_count=1, maintain_at=medivac_count_max)
            # if self.minerals >150 and self.vespene > 75:
            #    starport = self.units(UnitTypeId.STARPORT).ready.first
            #    self.combinedActions.append(starport.train(UnitTypeId.VIKING))
        if self.units(UnitTypeId.STARPORT).ready.exists:
            self.produce_force(UnitTypeId.STARPORT, UnitTypeId.VIKINGFIGHTER, batch_count=1, maintain_at=viking_count_max)

    def produce_tank_thor_viking_hellbat(self):
        # set a ceiling for unit count to avoid any single unit produced too much
        tank_count_max = max(10, self.units(UnitTypeId.MARINE).amount/4)
        thor_count_max= max(12, self.units(UnitTypeId.SIEGETANK).amount)
        viking_count_max = self.units(UnitTypeId.SIEGETANK).amount/2
        hellbat_count_max = self.units(UnitTypeId.SIEGETANK).amount*2
        battle_crusier_max = 10

        if self.units(UnitTypeId.FACTORYTECHLAB).ready.exists:
            self.produce_force(UnitTypeId.FACTORY, UnitTypeId.THOR, batch_count=1, maintain_at=thor_count_max)
            self.produce_force(UnitTypeId.FACTORY, UnitTypeId.SIEGETANK, batch_count=1, maintain_at=tank_count_max)
            self.produce_force(UnitTypeId.FACTORY, UnitTypeId.HELLION, batch_count=1, maintain_at=hellbat_count_max)
        if self.units(UnitTypeId.STARPORTTECHLAB).ready.exists:
            self.produce_force(UnitTypeId.STARPORT, UnitTypeId.BATTLECRUISER, batch_count=1, maintain_at=battle_crusier_max)
            self.produce_force(UnitTypeId.STARPORT, UnitTypeId.VIKINGFIGHTER, batch_count=1,
                               maintain_at=viking_count_max)

    def pump_force_terran(self):
        if self.game_stage == self.Stages.early:
            #print("pumping force for early stage")
            self.produce_tank_marine_medivac()
        elif self.game_stage == self.Stages.middle or self.game_stage == self.Stages.late:
            # print("pumping force for middle stage")
            self.produce_tank_thor_viking_hellbat()
        else:
            print("should not be here")
            print("game_stage", self.game_stage)

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
            # print("can attack now")
            return True
        else:
            return False

    def can_do_attack(self):
        return self.can_do_first_attack

    def get_unit_upper_limit(self, unit_type: 'UnitTypeId.SCV'):
        return self.unit_count_limit_per_base[unit_type] * (self.units(UnitTypeId.COMMANDCENTER).amount
                                                            + self.units(UnitTypeId.ORBITALCOMMAND).amount
                                                            + self.units(UnitTypeId.PLANETARYFORTRESS).amount)

    def get_attack_force(self):
        units = []
        for unit_type in [UnitTypeId.MARINE, UnitTypeId.SIEGETANK,
                          UnitTypeId.VIKINGFIGHTER, UnitTypeId.VIKINGASSAULT, UnitTypeId.MEDIVAC, UnitTypeId.THOR]:
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


    def neighbors4(self, position, distance=1):
        p = position
        d = distance
        return {
            Point2((p.x - d, p.y)),
            Point2((p.x + d, p.y)),
            Point2((p.x, p.y - d)),
            Point2((p.x, p.y + d)),
        }

    def neighbors8(self, position, distance=1):
        p = position
        d = distance
        return self.neighbors4(position, distance) | {
            Point2((p.x - d, p.y - d)),
            Point2((p.x - d, p.y + d)),
            Point2((p.x + d, p.y - d)),
            Point2((p.x + d, p.y + d)),
        }
