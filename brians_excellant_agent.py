
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

    async def offensive_force_buildings(self):
        sd = self.structures(UnitTypeId.SUPPLYDEPOT)
        print(sd)
        if self.can_afford(UnitTypeId.BARRACKS) and not self.already_pending(UnitTypeId.BARRACKS) and sd:
            await self.build(UnitTypeId.BARRACKS, near=sd.random.position)

    async def build_offensive_force(self):
        for racks in self.structures(UnitTypeId.BARRACKS).ready.idle:
            if self.can_afford(UnitTypeId.MARINE) and self.supply_left > 0:
                self.do(racks.train(UnitTypeId.MARINE))

    def find_target(self):
        if len(self.enemy_units) > 0:
            return random.choice(self.enemy_units)
        elif len(self.enemy_structures) > 0:
            return random.choice(self.enemy_structures)
        else:
            return self.enemy_start_locations[0]

    async def attack(self):
        if self.units(UnitTypeId.MARINE).amount > 15:
            for m in self.units(UnitTypeId.MARINE).idle:
                self.do(m.attack(self.find_target()))

        elif self.units(UnitTypeId.MARINE).amount > 3:
            if len(self.enemy_units) > 0:
                for m in self.units(UnitTypeId.MARINE).idle:
                    self.do(m.attack(random.choice(self.enemy_units)))

