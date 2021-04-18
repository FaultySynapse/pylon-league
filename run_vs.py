import sc2
from crushinator import Crushinator
from brians_excellent_agent import BrianBot
from sc2.player import Bot, Computer
sc2.run_game(
    sc2.maps.get("Simple64"),
    [Bot(sc2.Race.Zerg, Crushinator()), Bot(sc2.Race.Terran, BrianBot())],
    realtime=False,
)