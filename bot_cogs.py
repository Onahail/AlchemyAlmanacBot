import discord
import os

from discord.ext import commands
from dotenv import load_dotenv

from db import db

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.members = True
intents.message_content = True


class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=".", intents=intents)

    async def setup_hook(self):
        await db.connect()
        await db.init_utils()
        await self.load_extension('dm_commands')
        await self.load_extension('player_commands')
        await self.load_extension('available_crafts')
        await self.load_extension('crafting')
        await self.load_extension('lookup')
        await self.load_extension('admin')
        await self.load_extension('how-to')
        await self.load_extension('register')
        await self.load_extension('deregister')
        await self.load_extension('guild_events')

    async def on_ready(self):
        print(f"Logged in as {self.user}!")


bot = Bot()


def main():
    bot.run(TOKEN)
    #bot.tree.remove_command("add")
    #bot.tree.remove_command("available_crafts")
    #bot.tree.remove_command("craft")
    #bot.tree.remove_command("deregister")
    #bot.tree.remove_command("dm")
    #bot.tree.remove_command("how_to")
    #bot.tree.remove_command("inventory")
    #bot.tree.remove_command("lookup")
    #bot.tree.remove_command("register")
    #bot.tree.remove_command("sub")
    #bot.tree.remove_command("transfer")


if __name__ == "__main__":
    main()
