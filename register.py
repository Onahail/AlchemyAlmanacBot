import discord
import utils

from discord import app_commands, Embed
from discord.ext import commands

from db import db


class RegisterCommands(commands.GroupCog, group_name="register"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="dm",
        description="Register a new DM. Admin only.",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.autocomplete(username=utils.discord_member_autocompletion)
    async def register_dm(self, interaction, username: str):
        if "|" not in username:
            await interaction.response.send_message("That person is not a member of this server.")
            return
        user_display_name, discord_user_id_str = username.split("|")
        discord_user_id = int(discord_user_id_str)
        db_unique_server_id = await db.get_server_database_id(interaction.guild.id)
        dm = await db.get_server_dm(db_unique_server_id)

        if dm:
            dm_name = await utils.get_display_name(interaction, dm['user_id'])
            await interaction.response.send_message(
                f"{dm_name} is currently the server DM! Please deregister first if you want to change DMs.")
            return

        role_name = "Dungeon Master"
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if not role:
            role = await interaction.guild.create_role(name=role_name, reason="Needed for DM registration.")

        member = interaction.guild.get_member(discord_user_id)
        if not member:
            await interaction.response.send_message("Could not find the user in this server.")
            return

        await member.add_roles(role, reason="Registered as server DM")
        await db.register_dm(discord_user_id, db_unique_server_id)
        await interaction.response.send_message(
            f"{user_display_name} registered as the server DM and given the '{role_name}' role!"
            f" Have fun your adventures!")

    @utils.has_role("Dungeon Master")
    @app_commands.command(
        name="player",
        description="Registers a new player and adds an inventory for them. Dungeon Master only."
    )
    @app_commands.autocomplete(username=utils.discord_member_autocompletion)
    async def register_player(self, interaction, username: str, character_name: str):
        if "|" not in username:
            await interaction.response.send_message("That person is not a member of this server.")
            return
        user_display_name, discord_user_id_str = username.split("|")
        discord_user_id = int(discord_user_id_str)
        db_unique_server_id = await db.get_server_database_id(interaction.guild.id)
        players = await db.get_all_players(db_unique_server_id)

        for player in players:
            if player["user_id"] == discord_user_id and player["server_id"] == db_unique_server_id:
                await interaction.response.send_message(
                    f"{user_display_name} already has a registered character named {player['character_name']}.")
                return

        await db.register_player(discord_user_id, db_unique_server_id, character_name)
        await interaction.response.send_message(
            f"New character registered for {user_display_name}. Welcome to the party, {character_name}!")

    async def cog_app_command_error(self, interaction, error: app_commands.AppCommandError):
        # Default error message
        message = None

        if isinstance(error, app_commands.CheckFailure):
            message = "You do not have permission to use this command."

        elif isinstance(error, app_commands.CommandInvokeError):
            original = error.original
            if isinstance(original, discord.errors.Forbidden) and original.code == 50013:
                message = (
                    "I don't have permissions to assign the **Dungeon Master** role. "
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
    await bot.add_cog(RegisterCommands(bot))
