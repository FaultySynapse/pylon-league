import sc2
from crushinator import Crushinator
from sc2.player import Bot, Computer
sc2.run_game(
    sc2.maps.get("Simple64"),
    [Bot(sc2.Race.Zerg, Crushinator()), Computer(sc2.Race.Terran, sc2.Difficulty.Easy)],
    realtime=False,
)