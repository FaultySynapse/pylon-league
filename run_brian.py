import sc2
from brians_excellent_agent import BrianBot
from sc2.player import Bot, Computer


sc2.run_game(
    sc2.maps.get("WintersGateLE"),
    [Bot(sc2.Race.Terran, BrianBot()), Computer(sc2.Race.Zerg, sc2.Difficulty.Harder )],
    realtime=False,
)

