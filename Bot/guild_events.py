from discord.ext import commands
import discord
from db import db  # assuming you import your db wrapper


class GuildEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        join_message = (
            "Thanks for inviting me to your server! 🌱\n\n"
            "**To get started:**\n"
            "• Use `/register dm` to assign a Dungeon Master (**admin only**)\n"
            "• The DM can then register players with `/register player`\n"
            "• See `/how-to` for a full rundown of everything I can do!\n\n"
            "Lets the adventures begin!!"
        )

        print(f"Joined new server: {guild.name} ({guild.id})")
        # Attempt to send the message to the system channel
        if guild.system_channel is not None and guild.system_channel.permissions_for(guild.me).send_messages:
            await guild.system_channel.send(join_message)
            await db.register_new_server(guild.id)
            return

        # If no system channel or no permission to send, try to find a general channel
        for channel in guild.text_channels:
            if channel.name == "general" and channel.permissions_for(guild.me).send_messages:
                await channel.send(join_message)
                await db.register_new_server(guild.id)
                return

        # If no general channel or no permissions, send to the first available text channel
        if guild.text_channels and guild.text_channels[0].permissions_for(guild.me).send_messages:
            await guild.text_channels[0].send(join_message)
            await db.register_new_server(guild.id)
            return

        # If all attempts fail, inform that no suitable channel was found
        print(f"Could not find an appropriate channel to send a greeting message in {guild.name}")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        print(f"Bot was removed from: {guild.name} ({guild.id})")
        db_unique_server_id = await db.get_server_database_id(guild.id)
        # Remove from database
        await db.remove_server(db_unique_server_id)


async def setup(bot):
    await bot.add_cog(GuildEvents(bot))