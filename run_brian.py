import sc2
from brians_excellant_agent import BriansExcellantAgent
from sc2.player import Bot, Computer
sc2.run_game(
    sc2.maps.get("Simple64"),
    [Bot(sc2.Race.Terran, BriansExcellantAgent()), Computer(sc2.Race.Zerg, sc2.Difficulty.Easy)],
    realtime=False,
)