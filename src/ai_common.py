

import random
import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer

_NORMAL_BUILD_ORDER_PROTOSS=[PYLON,GATEWAY,CYBERNETICSCORE,STARGATE]
_NORMAL_BUILD_ORDER_TERRAN=[(SUPPLYDEPOT,1), (BARRACKS,1),(FACTORY,1),(STARPORT,1),(ENGINEERINGBAY,1),(ARMORY,1)]


class CeacarBot(sc2.BotAI):
    build_order_index = 0
    build_order = _NORMAL_BUILD_ORDER_TERRAN

    game_stage = "early"
    supply_gap = {"early":3, "middle":4, "late":6}

    def __init__(self):
        pass

    def no_base(self,base_type:'sc2.contants.NEXUS'):
        return not self.units(base_type).exists

    def get_base(self, base_name:'sc2.constants.COMMANDCENTER'):
        ccs = self.units(base_name)
        cc = ccs.first
        return cc

    async def build_refinary(self, refinary_name:'sc2.constatns.REFINARY', base_name:'sc2.constants.COMMANDCENTER'):
        cc = self.get_base(base_name)
        if self.workers.amount > 11 and self.units(UnitTypeId.SUPPLYDEPOT).ready.exists and self.can_afford(refinary_name):
            vgs = self.state.vespene_geyser.closer_than(20.0, cc)
            for vg in vgs:
                if self.units(refinary_name).closer_than(1.0, vg).exists:
                    break

                worker = self.select_build_worker(vg.position)
                if worker is None:
                    break

                await self.do(worker.build(refinary_name, vg))
                break
        # workers should be allocated with when gas finish
        if self.units(refinary_name).ready.exists:
            await self.allocate_workers_for_gas(refinary_name)

    async def worker_suicide_attack(self):
        for worker in self.workers:
            await self.do(worker.attack(self.enemy_start_locations[0]))
        return True

    async def idle_worker_return_to_work(self):
        #potential issue of how to find nearest cc for the scv
        for cc in self.units(self.BASE):
            for scv in self.units(SCV).idle:
                await self.do(scv.gather(self.state.mineral_field.closest_to(cc)))

    async def max_worker_if_can(self, worker_type: 'sc2.constants.PROBE', base_instance: 'sc2.constants.NEXUS'):
        if self.workers.amount < 16 and base_instance.noqueue:
            if self.can_afford(worker_type):
                await self.do(base_instance.train(worker_type))

    async def add_units_cap_if_needed(self, near_place:"sc2.constants.COMMANDCENTER"):
        if self.supply_left < self.supply_gap[self.game_stage]:
            if self.can_afford(SUPPLYDEPOT):
                await self.build(SUPPLYDEPOT, near= self.determine_build_location(near_place))

    def determine_build_location(self, base:'sc2.constants.COMMANDCENTER'):
        all_bases = self.units(base)
        base = all_bases.first
        pos = base.position.towards_with_random_angle(self.game_info.map_center, 16)
        return pos

    def update_build_order(self, building, count):

        if count == 0:
            self.build_order_index = self.build_order_index + 1
            print("build_order_index increased to", self.build_order_index)
            return

        self.build_order[self.build_order_index] = building, count - 1
        print("updated build_order:", building, count)

    async def build_needed_structure(self, supply_unit: 'SUPPLYDEPOT', build_near_to: 'COMMANDCENTER'):
        #this solves that not building first supply depot
        if self.workers.amount > 8:
            if not self.units(SUPPLYDEPOT).exists:
                await self.build(SUPPLYDEPOT, near=self.determine_build_location(build_near_to))
        if self.build_order_index > len(self.build_order) - 1:
            print("build_order exhausted")
            return
        building, count = self.build_order[self.build_order_index]
        print("checking to build:", building, count)
        print("comparing amount with count:", self.units(building).amount, count)
        if self.units(building).amount < count:
            #if not self.units(building).exists:
            print("building",building, "not exist")
            housing = self.units(supply_unit).ready
            print("is housing ready?", housing)
            if housing.exists:
                if self.can_afford(building):
                    print("can afford:", building)
                    self.update_build_order(building, count)
                    await self.build(building, near=self.determine_build_location(build_near_to))
        else:
            #has already built enough, this solves first supply depot issue
            self.update_build_order(building, count)

    def retrieve_abilities(self, selected_unit: 'a real unit'):
        abilities = self.get_available_abilities(selected_unit)
        return abilities

    async def use_ability(self, unit:'UnitTypeId.BARRACKS', ability:'AbilityId.HARVEST_GATHER_MULE'):
        selected_unit = self.units(unit).ready.first
        abilities = self.retrieve_abilities(selected_unit)

        if ability in abilities:
            await self.do(selected_unit(ability))

    async def upgrade_ability(self, unit:'a real unit like BARRACKS', ability:'AbilityId.RESEARCH_ADAPTIVETALONS'):
        abilities = await self.get_available_abilities(unit)
        if ability in abilities:
            print("found ability:", ability)
            if self.can_afford(ability) and unit.noqueue:
                print("upgrading ability", ability)
                await self.do(unit(ability))

    async def allocate_workers_for_gas(self, refinery_type:'REFINERY'):
        for ref in self.units(refinery_type):
            if ref.assigned_harvesters < ref.ideal_harvesters:
                worker = self.workers.closer_than(20, ref)
                if worker.exists:
                    await self.do(worker.random.gather(ref))

    # TERRAN SPECIALITY
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

    async def produce_force(self, building: 'UnitTypeId.BARRACKS', unit: 'UnitTypeId.MARINE', batch_count=1, maintain_at=999):
        if self.units(unit).amount >= maintain_at:
            # maintain unit at a level
            return
        counter = 0
        for producer in self.units(building):
            if self.can_afford(unit):
                print("producing", unit, "from", building)
                await self.do(producer.train(unit))
                counter = counter + 1
            if counter >= batch_count:
                # has queued targeted number
                break

    async def pump_force_terran(self):
        if self.units(UnitTypeId.BARRACKS).ready.exist:
            await self.produce_force(UnitTypeId.BARRACKS, UnitTypeId.Marine, batch_count=1)
        if self.units(UnitTypeId.FACTORY).ready.exist:
            tank_count_max = self.units(UnitTypeId.MARINE).amount/4
            await self.produce_force(UnitTypeId.FACTORY, UnitTypeId.SIEGETANK, batch_count=1, maintain_at=tank_count_max)
        if self.units(UnitTypeId.STARPORT).ready.exist:
            # viking_count_max = self.units(UnitTypeId.SIEGETANK).amount
            viking_count_max = 4
            await self.produce_force(UnitTypeId.FACTORY, UnitTypeId.SIEGETANK, batch_count=1, maintain_at=viking_count_max)

    async def drop_mule(self):
        ccs = self.units(UnitTypeId.COMMANDCENTER)
        cc = ccs.first
        for cc in ccs:
            if cc.energy_percentage.__ge__(80):
                await self.use_ability(cc, AbilityId.HARVEST_GATHER_MULE)

    # PROTOSS SPECIALITY
    async def build_forward_pylon(self):
        if self.units(PYLON).amount < 2:
            if self.can_afford(PYLON):
                pos = self.enemy_start_locations[0].towards(self.game_info.map_center, random.randrange(8, 15))
                await self.build(PYLON, near=pos)
