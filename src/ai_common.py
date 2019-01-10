import random
import sc2
from sc2.constants import *
from sc2.position import Point3, Point2
from sc2.unit import Unit
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId


class BotCommon(sc2.BotAI):

    def __init__(self):
        self.combinedActions = []
        self.build_order_index = 0
        self.build_order = []
        # self.game_stage = "early"
        # self.supply_gap = {"early":3, "middle":4, "late":6}
        self.expansion_ramp = None
        self.enemy_expansion_ramp = None
        self.SUPPLY_DEPOT_TYPE = None

    def no_base(self, base_type: 'sc2.contants.NEXUS'):
        return not self.units(base_type).exists

    def get_base(self, base_name: 'sc2.constants.COMMANDCENTER'):
        ccs = self.units(base_name)
        cc = ccs.first
        return cc

    def get_supply_depot_count(self):
        return self.units(self.SUPPLY_DEPOT_TYPE).amount + self.already_pending(self.SUPPLY_DEPOT_TYPE).amount

    def select_worker_for_building(self) -> 'Unit':
        if self.workers.idle.amount > 0:
            workergroup = self.workers.idle
        else:
            workergroup = self.workers.gathering

        selected_worker = workergroup.furthest_to(workergroup.center)
        return selected_worker

    async def expand_base(self, base_name: 'UnitTypeId.COMMANDCENTER'):
        # expand if we can afford and have less than 2 bases
        if 1 <= self.townhalls.amount < 2 \
                and self.already_pending(base_name) == 0 \
                and self.can_afford(base_name):
            # get_next_expansion returns the center of the mineral fields of the next nearby expansion
            next_expo = await self.get_next_expansion()
            # from the center of mineral fields, we need to find a valid place to place the command center
            location = await self.find_placement(base_name, next_expo, placement_step=1)
            if location:
                # now we "select" (or choose) the nearest worker to that found location
                w = self.select_build_worker(location)
                if w and self.can_afford(UnitTypeId.COMMANDCENTER):
                    # the worker will be commanded to build the command center
                    error = await self.do(w.build(UnitTypeId.COMMANDCENTER, location))
                    if error:
                        print(error)

    async def build_refinary(self, refinary_name: 'sc2.constatns.REFINERY', base_name: 'sc2.constants.COMMANDCENTER'):
        cc = self.get_base(base_name)
        if self.workers.amount > 13 \
                and self.get_supply_depot_count() > 0 \
                and self.can_afford(refinary_name):
            vgs = self.state.vespene_geyser.closer_than(15.0, cc)
            for vg in vgs:
                if self.units(refinary_name).closer_than(1.0, vg).exists:
                    break

                worker = self.select_build_worker(vg.position)
                if worker is None:
                    break

                self.combinedActions.append(worker.build(refinary_name, vg))
                break
        # workers should be allocated with when gas finish
        if self.units(refinary_name).ready.exists:
            # await self.allocate_workers_for_gas(refinary_name)
            for ref in self.units(refinary_name):
                if ref.assigned_harvesters < ref.ideal_harvesters:
                    await self.distribute_workers()

    def worker_suicide_attack(self):
        for worker in self.workers:
            self.combinedActions.append(worker.attack(self.enemy_start_locations[0]))
        return True

    def idle_worker_return_to_work(self):
        if self.townhalls.exists:
            for w in self.workers.idle:
                th = self.townhalls.closest_to(w)
                mfs = self.state.mineral_field.closer_than(10, th)
                if mfs:
                    mf = mfs.closest_to(w)
                    self.combinedActions.append(w.gather(mf))

    def max_worker_if_can(self, worker_type: 'sc2.constants.PROBE', base_instance: 'sc2.constants.NEXUS'):
        if self.workers.amount < 18 * self.townhalls.amount and base_instance.noqueue:
            if self.can_afford(worker_type):
                self.combinedActions.append(base_instance.train(worker_type))

    def count_building(self, building_type: ''):
        return self.units(building_type).amount + self.already_pending(building_type)

    def get_sorted_ramp(self, near_to_location: 'self.start_location'):
        # only two ramp are in game one is start location ramp and enemy ramp
        return sorted(
            {ramp for ramp in self.game_info.map_ramps if len(ramp.upper2_for_ramp_wall) == 2},
            key=(lambda r: near_to_location.distance_to(r.top_center))
        )

    def get_main_base_ramp(self):
        # singleton pattern
        if self.expansion_ramp:
            return self.expansion_ramp

        # works on places with only one ramp for in and out
        sorted_ramp = self.get_sorted_ramp(self.start_location)
        # if len(sorted_ramp) > 1:
        #     return sorted_ramp[1]
        # elif len(sorted_ramp) > 0:
        #     return sorted_ramp[0]
        # else:
        #     return None
        return sorted_ramp[0]

    def get_enemy_expansion_ramp(self):
        # singleton pattern
        if self.enemy_expansion_ramp:
            return self.enemy_expansion_ramp

        # works on places with only one ramp for in and out
        sorted_ramp = self.get_sorted_ramp(self.enemy_start_locations[0])
        # if len(sorted_ramp) > 1:
        #     return sorted_ramp[1]
        # elif len(sorted_ramp) > 0:
        #     return sorted_ramp[0]
        # else:
        #     return None
        return sorted_ramp[1]

    def move_to_enemy_location(self, units: 'list of real units can attack'):
        # rally to furthest
        furthest_depot = self.select_furthest_depot_unit()
        if furthest_depot:
            self.rally_to_position(units, furthest_depot.position)
        else:
            # skip this move if no supply unit is ready
            return
        # check if all units are in rally point
        unit_grouped = True

        if furthest_depot:
            # check if unit is all grouped up
            for unit in units:
                unit_away_distance = unit.distance_to(furthest_depot.position)
                if unit_away_distance > 12:
                    print(unit, "is away from group point by", unit_away_distance)
                    unit_grouped = False

        for unit in units:
            # target = self.known_enemy_structures.random_or(self.enemy_start_locations[0]).position
            # self.combinedActions.append(unit.attack(target))
            if furthest_depot:
                if unit_grouped:
                    loc = random.choice(self.enemy_start_locations[0])
                    print("attack enemy base at", loc)
                    if loc:
                        self.combinedActions.append(unit.attack(loc))

    def is_enemy_insight(self, near_building:'a building unit'):
        enemy_threats_nearby = self.is_enemy_nearby(near_building, 30)
        if enemy_threats_nearby:
            return True
        else:
            return False

    def enemy_nearby(self, near_to_unit:'enemy near this unit', distance:'distance to this unit'):
        enemy_threats_nearby = self.known_enemy_units.filter(lambda x: x.can_attack_ground).closer_than(distance, near_to_unit)
        return enemy_threats_nearby

    def select_furthest_depot_unit(self):
        return self.select_furthest(
            self.units(self.SUPPLY_DEPOT_TYPE),
            self.townhalls.first)

    def defend_base(self, defend_units: 'list of real units'):
        for cc in self.townhalls:
            enemy_threats_near_base = self.enemy_nearby(cc, 35)
            if enemy_threats_near_base:
                for unit in defend_units:
                    self.combinedActions.append(unit.attack(enemy_threats_near_base.first))
            else:
                furthest_supply_depot_unit = self.select_furthest_depot_unit()
                if furthest_supply_depot_unit:
                    self.rally_to_position(defend_units, furthest_supply_depot_unit.position)

    def attack_enemy(self, units: 'list of real units can attack'):
        # ready to attack, shoot nearest ground unit
        for r in units:
            enemyGroundUnits = self.known_enemy_units.not_flying.closer_than(14, r)  # hardcoded attackrange of 5
            if r.weapon_cooldown == 0 and enemyGroundUnits.exists:
                enemyGroundUnits = enemyGroundUnits.sorted(lambda x: x.distance_to(r))
                closestEnemy = enemyGroundUnits[0]
                self.combinedActions.append(r.attack(closestEnemy))
                continue  # continue for loop, dont execute any of the following

    async def add_units_cap_if_needed(self, supply_name: 'UnitTypeId.SUPPLYDEPOT'):
        # add supply depot only when no other supply depot is building
        # if self.supply_left < self.supply_gap[self.game_stage] and self.already_pending(UnitTypeId.SUPPLYDEPOT) == 0:
        if self.supply_left < 5 \
                and self.townhalls.exists \
                and self.supply_used >= 14 \
                and self.can_afford(UnitTypeId.SUPPLYDEPOT) \
                and self.units(UnitTypeId.SUPPLYDEPOT).not_ready.amount + \
                self.already_pending(UnitTypeId.SUPPLYDEPOT) < 1:
            if self.can_afford(supply_name):
                print("supply_left", self.supply_left)
                print("pending depopt count:",self.units(UnitTypeId.SUPPLYDEPOT).not_ready.amount + self.already_pending(UnitTypeId.SUPPLYDEPOT) < 1)
                print("build depot")
                worker = self.select_worker_for_building()
                loc = await self.determine_build_location(supply_name, self.townhalls.first.position, placement_gap=1)
                self.combinedActions.append(worker.build(supply_name, loc))

    async def determine_build_location(self, building: 'UnitTypeId.BARRACKS', \
                                       unit_nearby: 'a real unit like self.townhalls.first', \
                                       placement_gap=6):
        return await self.find_placement(building, unit_nearby, placement_step=placement_gap)

    async def build_the_very_first_supply_building(self, supply_unit: 'UnitTypeId.SUPPLYDEPOT',
                                                   build_near_to: 'UnitTypeId.COMMANDCENTER'):
        if self.workers.amount > 8:
            if not self.units(supply_unit).exists:
                worker = self.select_worker_for_building()
                loc = await self.determine_build_location(supply_unit, self.townhalls.first.position)
                if loc:
                    self.combinedActions.append(worker.build(UnitTypeId.SUPPLYDEPOT, loc))

    async def build_needed_structure(self, supply_unit: 'SUPPLYDEPOT', build_near_to: 'COMMANDCENTER'):
        if not self.get_supply_depot_count() > 0:
            await self.build_the_very_first_supply_building(supply_unit, build_near_to)
            return

        if self.build_order_index > len(self.build_order) - 1:
            # print("build_order exhausted:",self.build_order_index, ">", len(self.build_order), "-1")
            return
        building, count = self.build_order[self.build_order_index]
        # print("what to build:", building, count)
        # print(building, "current building count vs max_count:", self.units(building).amount, count)
        if self.count_building(building) < count:
            if self.can_afford(building):
                # print("can afford:", building)
                worker = self.select_worker_for_building()
                if not worker:
                    return
                loc = await self.determine_build_location(supply_unit, self.townhalls.first.position)
                if loc:
                    self.combinedActions.append(worker.build(building, loc))
        if self.count_building(building) >= count:
            print("built enough ", building)
            self.build_order_index = self.build_order_index + 1

    def retrieve_abilities(self, selected_unit: 'a real unit'):
        abilities = self.get_available_abilities(selected_unit)
        return abilities

    def use_ability(self, unit: 'UnitTypeId.COMMANDCENTER', ability: 'AbilityId.HARVEST_GATHER_MULE'):
        selected_unit = self.units(unit).ready.first
        abilities = self.retrieve_abilities(selected_unit)

        if ability in abilities:
            self.combinedActions.append(selected_unit(ability))

    def rally_to_position(self, units: 'real units', position: 'a coordinate'):
        # units will move to furthest of the building type
        # ramp = self.get_main_base_ramp()
        # ramp_pos = ramp.corner_depots.pop()
        # print("moving to ramp pos:",ramp_pos)
        # if units and ramp_pos:

        for unit in units:
            self.combinedActions.append(unit.attack(position))

    def select_furthest(self, units: 'real units', reference_unit: 'a real unit')-> 'furthest unit to reference_unit':
        sorted_units = units.sorted(lambda x: x.distance_to(reference_unit))
        if sorted_units:
            return sorted_units.pop()

    """
   if self.units(BARRACKSTECHLAB).ready.exists:
  for lab in self.units(BARRACKSTECHLAB).ready:
    abilities = await self.get_available_abilities(lab)
    if AbilityId.RESEARCH_COMBATSHIELD in abilities and \
       self.can_afford(AbilityId.RESEARCH_COMBATSHIELD):
       await self.do(lab(AbilityId.RESEARCH_COMBATSHIELD)) 
    """

    async def upgrade_ability(self, unit: 'a real unit like BARRACKS', ability: 'AbilityId.RESEARCH_ADAPTIVETALONS'):
        abilities = await self.get_available_abilities(unit)
        if ability in abilities:
            print("found ability:", ability)
            if self.can_afford(ability) and unit.noqueue:
                print("upgrading ability", ability)
                await self.do(unit(ability))

    def allocate_workers_for_gas(self, refinery_type: 'REFINERY'):
        for ref in self.units(refinery_type):
            if ref.assigned_harvesters < ref.ideal_harvesters:
                worker = self.workers.closer_than(20, ref)
                if worker.exists:
                    self.combinedActions.append(worker.random.gather(ref))
                    # await self.do(worker.random.gather(ref))

    # Stolen from python-sc2 exmaples terran mass reaper example
    def in_pathing_grid(self, pos):
        # returns True if it is possible for a ground unit to move to pos - doesnt seem to work on ramps or near edges
        assert isinstance(pos, (Point2, Point3, Unit))
        pos = pos.position.to2.rounded
        return self._game_info.pathing_grid[(pos)] != 0

        # stolen and modified from position.py

    def neighbors4(self, position, distance=1):
        p = position
        d = distance
        return {
            Point2((p.x - d, p.y)),
            Point2((p.x + d, p.y)),
            Point2((p.x, p.y - d)),
            Point2((p.x, p.y + d)),
        }

        # stolen and modified from position.py

    def neighbors8(self, position, distance=1):
        p = position
        d = distance
        return self.neighbors4(position, distance) | {
            Point2((p.x - d, p.y - d)),
            Point2((p.x - d, p.y + d)),
            Point2((p.x + d, p.y - d)),
            Point2((p.x + d, p.y + d)),
        }

    # already pending function rewritten to only capture units in queue and queued buildings
    # the difference to bot_ai.py alredy_pending() is: it will not cover structures in construction
    def already_pending(self, unit_type):
        ability = self._game_data.units[unit_type.value].creation_ability
        unitAttributes = self._game_data.units[unit_type.value].attributes

        buildings_in_construction = self.units.structure(unit_type).not_ready
        if 8 not in unitAttributes and any(o.ability == ability for w in (self.units.not_structure) for o in w.orders):
            return sum([o.ability == ability for w in (self.units - self.workers) for o in w.orders])
        # following checks for unit production in a building queue, like queen, also checks if hatch is morphing to LAIR
        elif any(o.ability.id == ability.id for w in (self.units.structure) for o in w.orders):
            return sum([o.ability.id == ability.id for w in (self.units.structure) for o in w.orders])
        # the following checks if a worker is about to start a construction (and for scvs still constructing if not checked for structures with same position as target)
        elif any(o.ability == ability for w in self.workers for o in w.orders):
            return sum([o.ability == ability for w in self.workers for o in w.orders]) \
                   - buildings_in_construction.amount
        elif any(egg.orders[0].ability == ability for egg in self.units(UnitTypeId.EGG)):
            return sum([egg.orders[0].ability == ability for egg in self.units(UnitTypeId.EGG)])
        return 0

    # distribute workers function rewritten,
    # the default distribute_workers() function did not saturate gas quickly enough
    async def distribute_workers(self, performanceHeavy=True, onlySaturateGas=False):
        # expansion_locations = self.expansion_locations
        # owned_expansions = self.owned_expansions

        mineralTags = [x.tag for x in self.state.units.mineral_field]
        # gasTags = [x.tag for x in self.state.units.vespene_geyser]
        geyserTags = [x.tag for x in self.geysers]

        workerPool = self.units & []
        workerPoolTags = set()

        # find all geysers that have surplus or deficit
        deficitGeysers = {}
        surplusGeysers = {}
        for g in self.geysers.filter(lambda x: x.vespene_contents > 0):
            # only loop over geysers that have still gas in them
            deficit = g.ideal_harvesters - g.assigned_harvesters
            if deficit > 0:
                deficitGeysers[g.tag] = {"unit": g, "deficit": deficit}
            elif deficit < 0:
                surplusWorkers = self.workers.closer_than(10, g).filter(
                    lambda w: w not in workerPoolTags and len(w.orders) == 1 and w.orders[0].ability.id in [
                        AbilityId.HARVEST_GATHER] and w.orders[0].target in geyserTags)
                # workerPool.extend(surplusWorkers)
                for i in range(-deficit):
                    if surplusWorkers.amount > 0:
                        w = surplusWorkers.pop()
                        workerPool.append(w)
                        workerPoolTags.add(w.tag)
                surplusGeysers[g.tag] = {"unit": g, "deficit": deficit}

        # find all townhalls that have surplus or deficit
        deficitTownhalls = {}
        surplusTownhalls = {}
        if not onlySaturateGas:
            for th in self.townhalls:
                deficit = th.ideal_harvesters - th.assigned_harvesters
                if deficit > 0:
                    deficitTownhalls[th.tag] = {"unit": th, "deficit": deficit}
                elif deficit < 0:
                    surplusWorkers = self.workers.closer_than(10, th).filter(
                        lambda w: w.tag not in workerPoolTags and len(w.orders) == 1 and w.orders[0].ability.id in [
                            AbilityId.HARVEST_GATHER] and w.orders[0].target in mineralTags)
                    # workerPool.extend(surplusWorkers)
                    for i in range(-deficit):
                        if surplusWorkers.amount > 0:
                            w = surplusWorkers.pop()
                            workerPool.append(w)
                            workerPoolTags.add(w.tag)
                    surplusTownhalls[th.tag] = {"unit": th, "deficit": deficit}

            if all([len(deficitGeysers) == 0, len(surplusGeysers) == 0,
                    len(surplusTownhalls) == 0 or deficitTownhalls == 0]):
                # cancel early if there is nothing to balance
                return

        # check if deficit in gas less or equal than what we have in surplus,
        # else grab some more workers from surplus bases
        deficit_gas_count = sum(
            gasInfo["deficit"] for gasTag, gasInfo in deficitGeysers.items() if gasInfo["deficit"] > 0)
        surplus_count = sum(-gasInfo["deficit"] for gasTag, gasInfo in surplusGeysers.items() if gasInfo["deficit"] < 0)
        surplus_count += sum(-thInfo["deficit"] for thTag, thInfo in surplusTownhalls.items() if thInfo["deficit"] < 0)

        if deficit_gas_count - surplus_count > 0:
            # grab workers near the gas who are mining minerals
            for gTag, gInfo in deficitGeysers.items():
                if workerPool.amount >= deficit_gas_count:
                    break
                workers_near_gas = self.workers.closer_than(10, gInfo["unit"]).filter(
                    lambda w: w.tag not in workerPoolTags and len(w.orders) == 1 and w.orders[0].ability.id in [
                        AbilityId.HARVEST_GATHER] and w.orders[0].target in mineralTags)
                while workers_near_gas.amount > 0 and workerPool.amount < deficit_gas_count:
                    w = workers_near_gas.pop()
                    workerPool.append(w)
                    workerPoolTags.add(w.tag)

        # now we should have enough workers in the pool to saturate all gases,
        # and if there are workers left over, make them mine at townhalls that have mineral workers deficit
        for gTag, gInfo in deficitGeysers.items():
            if performanceHeavy:
                # sort furthest away to closest (as the pop() function will take the last element)
                workerPool.sort(key=lambda x: x.distance_to(gInfo["unit"]), reverse=True)
            for i in range(gInfo["deficit"]):
                if workerPool.amount > 0:
                    w = workerPool.pop()
                    if len(w.orders) == 1 and w.orders[0].ability.id in [AbilityId.HARVEST_RETURN]:
                        self.combinedActions.append(w.gather(gInfo["unit"], queue=True))
                    else:
                        self.combinedActions.append(w.gather(gInfo["unit"]))

        if not onlySaturateGas:
            # if we now have left over workers, make them mine at bases with deficit in mineral workers
            for thTag, thInfo in deficitTownhalls.items():
                if performanceHeavy:
                    # sort furthest away to closest (as the pop() function will take the last element)
                    workerPool.sort(key=lambda x: x.distance_to(thInfo["unit"]), reverse=True)
                for i in range(thInfo["deficit"]):
                    if workerPool.amount > 0:
                        w = workerPool.pop()
                        mf = self.state.mineral_field.closer_than(10, thInfo["unit"]).closest_to(w)
                        if len(w.orders) == 1 and w.orders[0].ability.id in [AbilityId.HARVEST_RETURN]:
                            self.combinedActions.append(w.gather(mf, queue=True))
                        else:
                            self.combinedActions.append(w.gather(mf))
