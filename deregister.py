import discord
import utils

from discord import app_commands
from discord.ext import commands

from db import db


class DeregisterCommands(commands.GroupCog, group_name="deregister"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="dm",
        description="Removes the current server DM. Admin only."
    )
    @app_commands.autocomplete(username=utils.discord_member_autocompletion)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def deregister_dm(self, interaction, username: str):
        if "|" not in username:
            await interaction.response.send_message("That person is not a member of this server.")
            return
        user_display_name, discord_user_id_str = username.split("|")
        discord_user_id = int(discord_user_id_str)
        db_unique_server_id = await db.get_server_database_id(interaction.guild.id)
        dm = await db.get_server_dm(db_unique_server_id)

        if not dm:
            await interaction.response.send_message(f"This server doesn't have a DM to remove.")
            return

        command_display_name = await utils.get_display_name(interaction, discord_user_id)
        dm_display_name = await utils.get_display_name(interaction, dm['user_id'])

        if command_display_name != dm_display_name:
            await interaction.response.send_message(f"{command_display_name} is not your DM. Your server DM is {dm_display_name}")
            return

        member = interaction.guild.get_member(discord_user_id)
        if member:
            role = discord.utils.get(interaction.guild.roles, name="Dungeon Master")
            if role in member.roles:
                await member.remove_roles(role, reason="Removed as server DM")

        await db.deregister_dm(discord_user_id, db_unique_server_id)
        await interaction.response.send_message(
            f"{user_display_name} has been ousted as DM! It's a mutiny!")

    @utils.has_role("Dungeon Master")
    @app_commands.command(
        name="player",
        description="Removes a player and their inventory from the database. Dungeon Master only."
    )
    @app_commands.autocomplete(username=utils.player_autocompletion)
    async def deregister_player(self, interaction, username: str):
        user_display_name, db_unique_player_id, db_unique_server_id = await utils.split_player_autocomplete_return_value(username)
        if db_unique_player_id == 0 or db_unique_server_id == 0:
            response = "That is not a player."
            await interaction.response.send_message(response)
            return

        players = await db.get_all_players(db_unique_server_id)
        character_exists = False
        character_name = None

        for player in players:
            if player["id"] == db_unique_player_id:
                character_exists = True
                character_name = player['character_name']

        if character_exists:
            await db.deregister_player(db_unique_player_id, db_unique_server_id)
            await interaction.response.send_message(f"{user_display_name}'s character {character_name} has been removed.")
        else:
            await interaction.response.send_message(f"{user_display_name} does not have a registered character.")

    async def cog_app_command_error(self, interaction, error: app_commands.AppCommandError):
        # Default error message
        message = None

        if isinstance(error, app_commands.CheckFailure):
            message = "You do not have permission to use this command."

        elif isinstance(error, app_commands.CommandInvokeError):
            original = error.original
            if isinstance(original, discord.errors.Forbidden) and original.code == 50013:
                message = (
                    "I don't have permissions to remove the **Dungeon Master** role. "
                    "Please move the role **below my highest role** in the server settings."
                )
            else:
                message = f"An error occurred while executing the command:\n```{original}```"

        else:
            message = f"An unexpected error occurred:\n```{error}```"

        # Respond safely based on whether the interaction was already handled
        if interaction.response.is_done():
            await interaction.followup.send(message)
        else:
            await interaction.response.send_message(message, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DeregisterCommands(bot))
