from sc2.bot_ai import BotAI
class BriansExcellantAgent(BotAI):
    async def on_step(self, iteration: int):
        print(f"This is my bot in iteration {iteration}!")