
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
from sc2.ids.ability_id import AbilityId
from sc2.position import Point2
from typing import Tuple, List



class BrianBot(sc2.BotAI):
    async def on_step(self, iteration):
        print(f"This is my bot in iteration {iteration}!")
        await self.distribute_workers()
        await self.build_workers()
        await self.build_supply_depots()
        await self.build_refineries()
        await self.expand()
        await self.offensive_force_buildings()
        await self.build_offensive_force()
        await self.attack()
        await self.handle_upgrades()

    async def build_workers(self):
        for cc in self.townhalls.ready:
            if self.can_afford(SCV):
                self.do(cc.train(UnitTypeId.SCV))


    async def build_supply_depots(self):

        cc = self.townhalls.random
        if self.can_afford(UnitTypeId.SUPPLYDEPOT) and self.supply_left < 10 and self.already_pending(UnitTypeId.SUPPLYDEPOT) < 1:
            print("Let's build a supply depot")
            await self.build(UnitTypeId.SUPPLYDEPOT, near=cc.position.towards(self.game_info.map_center, 8))


    async def build_refineries(self):
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
        if (
            1 <= self.townhalls.amount < 3
            and self.already_pending(UnitTypeId.COMMANDCENTER) == 0
            and self.can_afford(UnitTypeId.COMMANDCENTER)
        ):
            # get_next_expansion returns the position of the next possible expansion location where you can place a command center
            location: Point2 = await self.get_next_expansion()
            if location:
                # Now we "select" (or choose) the nearest worker to that found location
                worker: Unit = self.select_build_worker(location)
                if worker and self.can_afford(UnitTypeId.COMMANDCENTER):
                    # The worker will be commanded to build the command center
                    worker.build(UnitTypeId.COMMANDCENTER, location)

    def find_addon_points(self, racks_position: Point2):  # -> List[Point2]:
    # def find_addon_points():

        """ Return all points that need to be checked when trying to build an addon. Returns 4 points. """
        addon_offset: Point2 = Point2((2.5, -0.5))
        addon_position: Point2 = racks_position + addon_offset
        addon_points = [
            (addon_position + Point2((x - 0.5, y - 0.5))).rounded for x in range(0, 2) for y in range(0, 2)
        ]
        return addon_points

    async def offensive_force_buildings(self):
        sd = self.structures(UnitTypeId.SUPPLYDEPOT)
        print(sd)
        if self.can_afford(UnitTypeId.BARRACKS) and not self.already_pending(UnitTypeId.BARRACKS) and sd:
            await self.build(UnitTypeId.BARRACKS, near=sd.random.position)
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

    async def build_offensive_force(self):
        for racks in self.structures(UnitTypeId.BARRACKS).ready.idle:
            if self.supply_left > 0:
                # if racks.has_reactor:
                #     self.do(racks.train(UnitTypeId.MARINE, 2))
                # else:
                #     self.do(racks.train(UnitTypeId.MARINE))
                self.do(racks.train(UnitTypeId.MARINE))
                self.do(racks.train(UnitTypeId.MARINE))

    async def handle_upgrades(self):
        self.build_upgrade_buildings()
        self.do_upgrades()

    def build_upgrade_buildings(self):
        pass

    def do_upgrades(self):
        pass

    def find_target(self):
        if len(self.enemy_units) > 0:
            return random.choice(self.enemy_units)
        elif len(self.enemy_structures) > 0:
            return random.choice(self.enemy_structures)
        else:
            return self.enemy_start_locations[0]

    async def attack(self):
        if self.units(UnitTypeId.MARINE).amount > 30:
            for m in self.units(UnitTypeId.MARINE).idle:
                self.do(m.attack(self.find_target()))

        elif self.units(UnitTypeId.MARINE).amount > 10:
            if len(self.enemy_units) > 0:
                for m in self.units(UnitTypeId.MARINE).idle:
                    self.do(m.attack(random.choice(self.enemy_units)))
