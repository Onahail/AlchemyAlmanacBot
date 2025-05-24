import discord
import utils

from discord import app_commands, Embed
from discord.ext import commands

from db import db


class DungeonMasterCommands(commands.GroupCog, group_name="dm"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @utils.has_role("Dungeon Master")
    @app_commands.command(
        name="inventory",
        description="Retrieves any players inventory. Dungeon Master only.",
    )
    @app_commands.autocomplete(username=utils.player_autocompletion)
    async def inventory(self, interaction, username: str):
        await interaction.response.defer(thinking=True)
        user_display_name, db_unique_player_id, db_unique_server_id = await utils.split_player_autocomplete_return_value(username)
        if db_unique_player_id == 0 or db_unique_server_id == 0:
            response = "That is not a player."
            await interaction.followup.send(response)
            return

        role_color = await utils.get_role_color(interaction)

        player_inventory = await db.get_player_inventory(db_unique_player_id)
        player = await db.get_player(db_unique_player_id, db_unique_server_id)
        essences = []
        common_flora = []
        specialty_items = []

        if player:
            if player_inventory:
                title = "Inventory"

                embed = Embed(title=title, color=role_color)
                embed.set_author(name=player["character_name"], icon_url=interaction.user.display_avatar.url)

                for item in player_inventory:
                    if item["display_name"] in utils.essence_names:
                        essences.append(f"{item["display_name"]}: {item["quantity"]}")
                    elif item["display_name"] in utils.common_flora_names:
                        common_flora.append(f"{item["display_name"]}: {item["quantity"]}")
                    else:
                        specialty_items.append(f"{item["display_name"]}: {item["quantity"]}")

                embed.add_field(
                    name="Essences",
                    value="\n".join(essences) if essences else "None",
                    inline=False)

                embed.add_field(
                    name="Common Flora",
                    value="\n".join(common_flora) if common_flora else "None",
                    inline=False)

                embed.add_field(
                    name="Specialty Items",
                    value="\n".join(specialty_items) if specialty_items else "None",
                    inline=False)

                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    f"{player["character_name"]}'s inventory is empty! Go gather more stuff!")
        else:
            await interaction.followup.send("No inventory found for that player.")

    @utils.has_role("Dungeon Master")
    @app_commands.command(
        name="add",
        description="Add items to anybody's inventory. Dungeon Master only.",
    )
    @app_commands.describe(username="Which player?", component="Which item?", quantity="How much?")
    @app_commands.autocomplete(component=utils.component_autocompletion)
    @app_commands.autocomplete(username=utils.player_autocompletion)
    async def add_dm(self, interaction, username: str, component: str, quantity: int):
        _, db_unique_player_id, player, response = await utils.validate_player_and_components(username, component, quantity)
        if response:
            await interaction.response.send_message(response)
            return

        await db.add_player_inventory_item(db_unique_player_id, await utils.sanitize_input(component), quantity)
        await interaction.response.send_message(f"Added {quantity} {component} to {player["character_name"]}'s inventory!")

    @utils.has_role("Dungeon Master")
    @app_commands.command(
        name="sub",
        description="Subtract items to anyone's inventory. Dungeon Master Only"
    )
    @app_commands.autocomplete(component=utils.component_autocompletion)
    @app_commands.autocomplete(username=utils.player_autocompletion)
    @app_commands.describe(component="Which item?", quantity="How much?")
    async def sub_dm(self, interaction, username: str, component: str, quantity: int):
        _, db_unique_player_id, player, response = await utils.validate_player_and_components(username, component, quantity)
        if response:
            await interaction.response.send_message(response)
            return

        player_inventory = await db.get_player_inventory(db_unique_player_id)
        has_item, amount = await utils.check_inventory(player_inventory, component)

        if not has_item:
            await interaction.response.send_message(
                f"{player['character_name']} does not have any {component} in their inventory!")
            return

        if (amount - quantity) <= 0:
            await db.delete_player_inventory_item(db_unique_player_id, await utils.sanitize_input(component))
        else:
            await db.sub_player_inventory_item(db_unique_player_id, await utils.sanitize_input(component), quantity)
        await interaction.response.send_message(f"Removed {quantity} {component} to {player["character_name"]}'s inventory!")

    @utils.has_role("Dungeon Master")
    @app_commands.command(
        name="list",
        description="Returns a list of all your players. Dungeon Master Only"
    )
    async def dm_list(self, interaction):
        await interaction.response.defer()

        role_color = await utils.get_role_color(interaction)
        db_unique_server_id = await db.get_server_database_id(interaction.guild.id)
        players = await db.get_all_players(db_unique_server_id)
        players_list = []
        characters_list = []

        title = "Registered Players"

        embed = Embed(title=title, color=role_color)

        for player in players:
            display_name = await utils.get_display_name(interaction, player['user_id'])
            character_name = player['character_name']
            players_list.append(display_name)
            characters_list.append(character_name)

        embed.add_field(
            name="Player",
            value="\n".join(players_list),
            inline=True)

        embed.add_field(
            name="Character",
            value="\n".join(characters_list),
            inline=True)

        await interaction.followup.send(embed=embed)

    async def cog_app_command_error(self, interaction, error: app_commands.AppCommandError):
        # Default error message
        message = None

        if isinstance(error, app_commands.CheckFailure):
            message = "You do not have permission to use this command."

        elif isinstance(error, app_commands.CommandInvokeError):
            original = error.original
            message = f"An error occurred while executing the command:\n```{original}```"

        else:
            message = f"An unexpected error occurred:\n```{error}```"

        # Respond safely based on whether the interaction was already handled
        if interaction.response.is_done():
            await interaction.followup.send(message)
        else:
            await interaction.response.send_message(message, ephemeral=True)



async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DungeonMasterCommands(bot))