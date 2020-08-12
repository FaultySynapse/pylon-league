from sc2.bot_ai import BotAI
class Crushinator(BotAI):
    async def on_step(self, iteration: int):
        print(f"This is my bot in iteration {iteration}!")