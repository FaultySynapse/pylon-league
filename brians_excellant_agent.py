
# class BrianAgent(base_agent.BaseAgent):
#     def step(self, obs):
#         super(BrianAgent, self).step(obs)
#
#         return actions.FunctionCall(actions.FUNCTIONS.no_op.id, [])
# https://burnysc2.github.io/python-sc2/docs/text_files/introduction.html#creating-a-bot

import sc2
import random
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import *
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.ids.ability_id import AbilityId
from sc2.position import Point2
from typing import Tuple, List
from math import ceil


class BrianBot(sc2.BotAI):

    sufficient_marines_for_attack: bool = False
    ok_to_offensive_attack: bool = False

    async def on_step(self, iteration):
        await self.distribute_workers()
        await self.build_workers()
        await self.handle_supply_depots()
        await self.build_refineries()
        await self.expand()
        await self.offensive_force_buildings()
        await self.build_offensive_force()
        await self.attack()
        await self.handle_upgrades()
        await self.repair_buildings()
        await self.handle_townhalls()

    async def build_workers(self):
        num_scvs = self.units(UnitTypeId.SCV).amount
        num_ccs  = self.structures(UnitTypeId.COMMANDCENTER).amount - ceil(self.already_pending(UnitTypeId.COMMANDCENTER))

        for cc in self.townhalls.ready.idle:
            if self.can_afford(SCV) and num_scvs < num_ccs*22 and num_scvs<70 :
                self.do(cc.train(UnitTypeId.SCV))


    async def handle_supply_depots(self):
        if self.townhalls:
            cc = self.townhalls.random
            racks = self.units(UnitTypeId.BARRACKS)
            if self.can_afford(UnitTypeId.SUPPLYDEPOT) and self.supply_left < 10 and not self.already_pending(UnitTypeId.SUPPLYDEPOT) and not racks:
                await self.build(UnitTypeId.SUPPLYDEPOT, near=cc.position.towards(self.game_info.map_center, 12))
            elif self.can_afford(UnitTypeId.SUPPLYDEPOT) and self.supply_left < 20 and racks and self.already_pending(UnitTypeId.SUPPLYDEPOT) < 3:
                await self.build(UnitTypeId.SUPPLYDEPOT, near=cc.position.towards(self.game_info.map_center, 12))

        # Raise depos when enemies are nearby
        for depo in self.structures(UnitTypeId.SUPPLYDEPOT).ready:
            for unit in self.enemy_units:
                if unit.distance_to(depo) < 15:
                    break
            else:
                depo(AbilityId.MORPH_SUPPLYDEPOT_LOWER)

        # Lower depos when no enemies are nearby
        for depo in self.structures(UnitTypeId.SUPPLYDEPOTLOWERED).ready:
            for unit in self.enemy_units:
                if unit.distance_to(depo) < 10:
                    depo(AbilityId.MORPH_SUPPLYDEPOT_RAISE)
                    break

    async def build_refineries(self):
        sd = self.structures(UnitTypeId.SUPPLYDEPOT)
        if sd:
            for cc in self.townhalls.ready:
                vaspenes = self.vespene_geyser.closer_than(15.0, cc)
                for vaspene in vaspenes:
                    if not self.can_afford(UnitTypeId.REFINERY):
                        break
                    worker = self.select_build_worker(vaspene.position)
                    if worker is None:
                        break
                    if not self.units(UnitTypeId.REFINERY).closer_than(1.0, vaspene).exists:
                        self.do(worker.build(UnitTypeId.REFINERY, vaspene))

    async def expand(self):
        num_racks = self.structures(UnitTypeId.BARRACKS).amount
        if (
            1 <= self.townhalls.amount < 5
            and self.townhalls.amount < num_racks+1
            and self.already_pending(UnitTypeId.COMMANDCENTER) == 0
            and self.can_afford(UnitTypeId.COMMANDCENTER)
            # TODO: and self.units(UnitTypeId.MARINE).amount >= (self.townhalls.amount-1.25)*8
        ):
            # get_next_expansion returns the position of the next possible expansion location where you can place a command center
            location: Point2 = await self.get_next_expansion()
            if location:
                # Now we "select" (or choose) the nearest worker to that found location
                worker: Unit = self.select_build_worker(location)
                if worker and self.can_afford(UnitTypeId.COMMANDCENTER):
                    # The worker will be commanded to build the command center
                    worker.build(UnitTypeId.COMMANDCENTER, location)

    async def handle_townhalls(self):
        for cc in self.structures(UnitTypeId.COMMANDCENTER):
            if self.can_afford(UnitTypeId.ORBITALCOMMAND):
                cc(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)
        for oc in self.structures(UnitTypeId.ORBITALCOMMAND):
            if oc.energy >= 100:
                oc(AbilityId.CALLDOWNMULE_CALLDOWNMULE)

    def find_addon_points(self, racks_position: Point2):  # -> List[Point2]:
    # def find_addon_points():

        """ Return all points that need to be checked when trying to build an addon. Returns 4 points. """
        addon_offset: Point2 = Point2((2.5, -0.5))
        addon_position: Point2 = racks_position + addon_offset
        addon_points = [
            (addon_position + Point2((x - 0.5, y - 0.5))).rounded for x in range(0, 2) for y in range(0, 2)
        ]
        return addon_points

    def points_to_build_addon(self, sp_position: Point2) -> List[Point2]:
        """ Return all points that need to be checked when trying to build an addon. Returns 4 points. """
        addon_offset: Point2 = Point2((2.5, -0.5))
        addon_position: Point2 = sp_position + addon_offset
        addon_points = [
            (addon_position + Point2((x - 0.5, y - 0.5))).rounded for x in range(0, 2) for y in range(0, 2)
        ]
        return addon_points

    def land_positions(self, my_position: Point2) -> List[Point2]:
        """ Return all points that need to be checked when trying to land at a location where there is enough space to build an addon. Returns 13 points. """
        land_positions = [(my_position + Point2((x, y))).rounded for x in range(-1, 2) for y in range(-1, 2)]
        return land_positions + self.points_to_build_addon(my_position)

    async def repair_buildings(self):
        for structure in self.structures():
            if structure.health != structure.health_max:
                my_scv = self.units(UnitTypeId.SCV).random
                if not my_scv.is_repairing:
                    my_scv.repair(structure)

    async def offensive_force_buildings(self):
        sd = self.structures(UnitTypeId.SUPPLYDEPOT)
        racks   = self.structures(UnitTypeId.BARRACKS)
        facts   = self.structures(UnitTypeId.FACTORY)
        sps     = self.structures(UnitTypeId.STARPORT)
        ccs     = self.townhalls
        num_marines = self.units(UnitTypeId.MARINE).amount

        # Build barracks
        if sd and not racks:
            if self.can_afford(UnitTypeId.BARRACKS) and not self.already_pending(UnitTypeId.BARRACKS):
                await self.build(UnitTypeId.BARRACKS, near=sd.random.position)
        elif sps and sd:
            if racks.amount <= 3*sps.amount and racks.amount <= 3*ccs.amount:
                if self.can_afford(UnitTypeId.BARRACKS) and self.already_pending(UnitTypeId.BARRACKS)<3:
                    await self.build(UnitTypeId.BARRACKS, near=sd.random.position)

        # Build factories
        if racks and sd and not facts:
            if self.can_afford(UnitTypeId.FACTORY) and not self.already_pending(UnitTypeId.FACTORY):
                await self.build(UnitTypeId.FACTORY, near=sd.random.position)
        elif sps and racks and sd:
            if facts.amount <= sps.amount and num_marines > 18:
                if self.can_afford(UnitTypeId.FACTORY) and not self.already_pending(UnitTypeId.FACTORY):
                    await self.build(UnitTypeId.FACTORY, near=sd.random.position)

        # Build starports
        if facts and ccs and sd and not sps:
            if self.can_afford(UnitTypeId.STARPORT) and not self.already_pending(UnitTypeId.STARPORT):
                await self.build(UnitTypeId.STARPORT, near=sd.random.position)
        elif racks and facts and ccs and num_marines > 18 and sd:
            if sps.amount < ccs.amount:
                if self.can_afford(UnitTypeId.STARPORT) and not self.already_pending(UnitTypeId.STARPORT):
                    await self.build(UnitTypeId.STARPORT, near=sd.random.position)

        for racks in self.structures(UnitTypeId.BARRACKS).ready.idle:
            if not racks.has_add_on and self.can_afford(UnitTypeId.REACTOR):
                addon_points = self.find_addon_points(racks.position)
                if all(
                        self.in_map_bounds(addon_point)
                        and self.in_placement_grid(addon_point)
                        and self.in_pathing_grid(addon_point)
                        for addon_point in addon_points
                ):
                    racks.build(UnitTypeId.BARRACKSREACTOR)
                else:
                    racks(AbilityId.LIFT)

        for fact in self.structures(UnitTypeId.FACTORY).ready.idle:
            if not fact.has_add_on and self.can_afford(UnitTypeId.FACTORYTECHLAB):
                addon_points = self.find_addon_points(fact.position)
                if all(
                        self.in_map_bounds(addon_point)
                        and self.in_placement_grid(addon_point)
                        and self.in_pathing_grid(addon_point)
                        for addon_point in addon_points
                ):
                    fact.build(UnitTypeId.FACTORYTECHLAB)
                else:
                    fact(AbilityId.LIFT)

        for sp in self.structures(UnitTypeId.STARPORT).ready.idle:
            if not sp.has_add_on and self.can_afford(UnitTypeId.STARPORTREACTOR):
                addon_points = self.find_addon_points(sp.position)
                if all(
                        self.in_map_bounds(addon_point)
                        and self.in_placement_grid(addon_point)
                        and self.in_pathing_grid(addon_point)
                        for addon_point in addon_points
                ):
                    sp.build(UnitTypeId.STARPORTREACTOR)
                else:
                    sp(AbilityId.LIFT)

        for racks in self.structures(UnitTypeId.BARRACKSFLYING).idle:
            possible_land_positions_offset = sorted(
                (Point2((x, y)) for x in range(-10, 10) for y in range(-10, 10)),
                key=lambda point: point.x ** 2 + point.y ** 2,
            )
            offset_point: Point2 = Point2((-0.5, -0.5))
            possible_land_positions = (racks.position.rounded + offset_point + p for p in possible_land_positions_offset)
            for target_land_position in possible_land_positions:
                land_and_addon_points: List[Point2] = self.land_positions(target_land_position)
                if all(
                    self.in_map_bounds(land_pos) and self.in_placement_grid(land_pos) and self.in_pathing_grid(land_pos)
                    for land_pos in land_and_addon_points
                ):
                    racks(AbilityId.LAND, target_land_position)
                    break

        for fact in self.structures(UnitTypeId.FACTORYFLYING).idle:
            possible_land_positions_offset = sorted(
                (Point2((x, y)) for x in range(-10, 10) for y in range(-10, 10)),
                key=lambda point: point.x ** 2 + point.y ** 2,
            )
            offset_point: Point2 = Point2((-0.5, -0.5))
            possible_land_positions = (fact.position.rounded + offset_point + p for p in possible_land_positions_offset)
            for target_land_position in possible_land_positions:
                land_and_addon_points: List[Point2] = self.land_positions(target_land_position)
                if all(
                    self.in_map_bounds(land_pos) and self.in_placement_grid(land_pos) and self.in_pathing_grid(land_pos)
                    for land_pos in land_and_addon_points
                ):
                    fact(AbilityId.LAND, target_land_position)
                    break

        # Find a position to land for a flying starport so that it can build an addon
        for sp in self.structures(UnitTypeId.STARPORTFLYING).idle:
            possible_land_positions_offset = sorted(
                (Point2((x, y)) for x in range(-12, 12) for y in range(-12, 12)),
                key=lambda point: point.x ** 2 + point.y ** 2,
            )
            offset_point: Point2 = Point2((-0.5, -0.5))
            possible_land_positions = (sp.position.rounded + offset_point + p for p in possible_land_positions_offset)
            for target_land_position in possible_land_positions:
                land_and_addon_points: List[Point2] = self.land_positions(target_land_position)
                if all(
                    self.in_map_bounds(land_pos) and self.in_placement_grid(land_pos) and self.in_pathing_grid(land_pos)
                    for land_pos in land_and_addon_points
                ):
                    sp(AbilityId.LAND, target_land_position)
                    break

    async def build_offensive_force(self):
        num_marines = self.units(UnitTypeId.MARINE).amount
        num_medivacs = self.units(UnitTypeId.MEDIVAC).amount
        num_siegetanks = self.units(UnitTypeId.SIEGETANK).amount
        for racks in self.structures(UnitTypeId.BARRACKS).ready.idle:
            if self.supply_left > 7:
                self.do(racks.train(UnitTypeId.MARINE))
                self.do(racks.train(UnitTypeId.MARINE))
        for fact in self.structures(UnitTypeId.FACTORY).ready.idle:
            if self.supply_left > 5 and fact.has_add_on:
                self.do(fact.train(UnitTypeId.SIEGETANK))
        for sp in self.structures(UnitTypeId.STARPORT).ready.idle:
            if self.supply_left > 5 and num_medivacs*5 < num_marines:
                self.do(sp.train(UnitTypeId.MEDIVAC))
                self.do(sp.train(UnitTypeId.MEDIVAC))

    async def handle_upgrades(self):
        await self.build_upgrade_buildings()
        await self.do_upgrades()

    async def build_upgrade_buildings(self):
        num_ccs = self.townhalls.amount
        if self.townhalls:
            cc = self.townhalls.random
        racks   = self.structures(UnitTypeId.BARRACKS)
        facts   = self.structures(UnitTypeId.FACTORY)
        sps     = self.structures(UnitTypeId.STARPORT)
        eb      = self.structures(UnitTypeId.ENGINEERINGBAY)
        ar      = self.structures(UnitTypeId.ARMORY)

        if (self.can_afford(UnitTypeId.ENGINEERINGBAY)
            and not self.already_pending(UnitTypeId.ENGINEERINGBAY)
            and num_ccs >= 2
            and racks
            and len(eb) < 2
            and facts
            and sps
        ):
            await self.build(UnitTypeId.ENGINEERINGBAY, near=cc.position)
        if (self.can_afford(UnitTypeId.ARMORY)
            and not self.already_pending(UnitTypeId.ARMORY)
            and len(eb) == 2
            and not ar
            and facts
            and sps
        ):
            await self.build(UnitTypeId.ARMORY, near=cc.position)

    async def do_upgrades(self):
        ar = self.structures(UnitTypeId.ARMORY)
        for eb in self.structures(UnitTypeId.ENGINEERINGBAY):
            if not eb.orders:
                if self.can_afford(UpgradeId.TERRANINFANTRYWEAPONSLEVEL1) and (
                        self.already_pending_upgrade(TERRANINFANTRYWEAPONSLEVEL1) == 0):
                    eb.research(UpgradeId.TERRANINFANTRYWEAPONSLEVEL1)
                elif ar and self.can_afford(UpgradeId.TERRANINFANTRYWEAPONSLEVEL2) and (
                        self.already_pending_upgrade(TERRANINFANTRYWEAPONSLEVEL2) == 0) and (
                        self.already_pending_upgrade(TERRANINFANTRYWEAPONSLEVEL1) == 1):
                    eb.research(UpgradeId.TERRANINFANTRYWEAPONSLEVEL2)
                elif ar and self.can_afford(UpgradeId.TERRANINFANTRYWEAPONSLEVEL3) and (
                        self.already_pending_upgrade(TERRANINFANTRYWEAPONSLEVEL3) == 0) and (
                        self.already_pending_upgrade(TERRANINFANTRYWEAPONSLEVEL2) == 1):
                    eb.research(UpgradeId.TERRANINFANTRYWEAPONSLEVEL3)
                if self.can_afford(UpgradeId.TERRANINFANTRYARMORSLEVEL1) and (
                        self.already_pending_upgrade(TERRANINFANTRYARMORSLEVEL1) == 0):
                    eb.research(UpgradeId.TERRANINFANTRYARMORSLEVEL1)
                elif ar and self.can_afford(UpgradeId.TERRANINFANTRYARMORSLEVEL2) and (
                        self.already_pending_upgrade(TERRANINFANTRYARMORSLEVEL2) == 0) and (
                        self.already_pending_upgrade(TERRANINFANTRYARMORSLEVEL1) == 1):
                    eb.research(UpgradeId.TERRANINFANTRYARMORSLEVEL2)
                elif ar and self.can_afford(UpgradeId.TERRANINFANTRYARMORSLEVEL3) and (
                        self.already_pending_upgrade(TERRANINFANTRYARMORSLEVEL3) == 0) and (
                        self.already_pending_upgrade(TERRANINFANTRYARMORSLEVEL2) == 1):
                    eb.research(UpgradeId.TERRANINFANTRYARMORSLEVEL3)

    def find_target(self):
        if len(self.enemy_units) > 0:
            return random.choice(self.enemy_units)
        elif len(self.enemy_structures) > 0:
            return random.choice(self.enemy_structures)
        else:
            return self.enemy_start_locations[0]

    def defend_colony(self, offensive_unit):
        need_to_defend: bool = False

        closest_enemy = random.choice(self.enemy_units)
        for enemy in self.enemy_units:
            if offensive_unit.distance_to_squared(enemy) < offensive_unit.distance_to_squared(enemy):
                closest_enemy = enemy
            for cc in self.townhalls:
                if enemy.distance_to_squared(cc) < 40*40:
                    need_to_defend = True
        if need_to_defend:
            self.do(offensive_unit.attack(closest_enemy))

    def retreat(self, offensive_unit):
        closest_cc = self.townhalls.random
        for cc in self.townhalls:
            if offensive_unit.distance_to_squared(cc) < offensive_unit.distance_to_squared(closest_cc):
                closest_cc = cc
        offensive_unit.move(closest_cc.position)

    async def attack(self):
        if self.already_pending_upgrade(TERRANINFANTRYARMORSLEVEL2) == 1 \
                and self.already_pending_upgrade(TERRANINFANTRYWEAPONSLEVEL2) == 1:
            if not self.ok_to_offensive_attack:
                print("Okay to attack at time= " + str(self.time/60) + "m")
            self.ok_to_offensive_attack = True


        if self.units(UnitTypeId.MARINE).amount > 20:
            self.sufficient_marines_for_attack = True
        elif self.units(UnitTypeId.MARINE).amount < 12:
            self.sufficient_marines_for_attack = False

        if self.ok_to_offensive_attack:
            if self.sufficient_marines_for_attack:
                target = self.find_target()
                for offensive_unit in self.units(UnitTypeId.MARINE).idle + self.units(UnitTypeId.SIEGETANK).idle:
                    offensive_unit.attack(target)
            else:
                for offensive_unit in self.units(UnitTypeId.MARINE).idle + self.units(UnitTypeId.SIEGETANK).idle:
                    self.retreat(offensive_unit)
        elif self.units(UnitTypeId.MARINE).amount > 5:
            if len(self.enemy_units) > 0:
                for m in self.units(UnitTypeId.MARINE).idle:
                    self.defend_colony(m)
                for s in self.units(UnitTypeId.SIEGETANK).idle:
                    self.defend_colony(s)
        await self.handle_seige_tanks()
        await self.handle_medivacs()

    async def handle_seige_tanks(self):
        # Siege tanks when enemies are nearby
        for tank in self.units(UnitTypeId.SIEGETANK):
            for unit in self.enemy_units:
                if unit.distance_to(tank) < 12:
                    tank(AbilityId.SIEGEMODE_SIEGEMODE)
                    break
        # Unseige tanks when no enemies are nearby
        for tank in self.units(UnitTypeId.SIEGETANKSIEGED):
            if not self.enemy_units:
                tank(AbilityId.UNSIEGE_UNSIEGE)
            else:
                nearby_unit = False
                for unit in self.enemy_units:
                    if unit.distance_to(tank) < 20:
                        nearby_unit = True
                        break
                if not nearby_unit:
                    tank(AbilityId.UNSIEGE_UNSIEGE)

    async def handle_medivacs(self):
        marines = self.units(UnitTypeId.MARINE)
        for m in self.units(UnitTypeId.MEDIVAC).idle:
            healing = False
            for marine in marines.idle:
                if marine.health != marine.health_max:
                    m.move(marine.position)
                    healing = True
                    break
            if not healing and marines:
                m.move(marines.random)

