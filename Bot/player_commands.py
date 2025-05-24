import discord
import utils

from discord import app_commands, Embed
from discord.ext import commands

from db import db

class PlayerCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="add",
        description="Add items to your inventory."
    )
    @app_commands.autocomplete(component=utils.component_autocompletion)
    @app_commands.describe(component="Which item?", quantity="How much?")
    async def add(self, interaction, component: str, quantity: int):
        db_unique_server_id = await db.get_server_database_id(interaction.guild.id)
        db_unique_player_id = await db.get_player_database_id(interaction.user.id, db_unique_server_id)
        player = await db.get_player(db_unique_player_id, db_unique_server_id)

        if not player:
            await interaction.response.send_message(f"You dont have an inventory, {str(interaction.user.display_name)}! Are you even in this game?!!")
            return

        if response := await utils.validate_components(component, quantity):
            return await interaction.response.send_message(response)

        await db.add_player_inventory_item(db_unique_player_id, await utils.sanitize_input(component), quantity)
        await interaction.response.send_message(f"Added {quantity} {component} to {player["character_name"]}'s inventory!")

    @app_commands.command(
        name="sub",
        description="Subtract items to your inventory."
    )
    @app_commands.autocomplete(component=utils.component_autocompletion)
    @app_commands.describe(component="Which item?", quantity="How much?")
    async def sub(self, interaction, component: str, quantity: int):
        db_unique_server_id = await db.get_server_database_id(interaction.guild.id)
        db_unique_player_id = await db.get_player_database_id(interaction.user.id, db_unique_server_id)
        player = await db.get_player(db_unique_player_id, db_unique_server_id)

        if not player:
            await interaction.response.send_message(
                f"{str(interaction.user.display_name)}... why are you trying to remove items when you dont even have an inventory to store them in...")
            return

        if response := await utils.validate_components(component, quantity):
            return await interaction.response.send_message(response)

        player_inventory = await db.get_player_inventory(db_unique_player_id)
        has_item, amount = await utils.check_inventory(player_inventory, component)

        if has_item:
            if amount - quantity <= 0:
                await db.delete_player_inventory_item(db_unique_player_id, await utils.sanitize_input(component))
                response = f"All {component} removed from {player["character_name"]}'s inventory!"
            else:
                await db.sub_player_inventory_item(db_unique_player_id, await utils.sanitize_input(component), quantity)
                response = f"Removed {quantity} {component} to {player["character_name"]}'s inventory!"
        else:
            response = f"You dont have any {component} in your inventory {player["character_name"]}! Go find some!"

        await interaction.response.send_message(response)

    @app_commands.command(
        name="inventory",
        description="Retrieves player inventory."
    )
    async def inventory(self, interaction):
        await interaction.response.defer(thinking=True)
        role_color = await utils.get_role_color(interaction)

        db_unique_server_id = await db.get_server_database_id(interaction.guild.id)
        db_unique_player_id = await db.get_player_database_id(interaction.user.id, db_unique_server_id)
        player = await db.get_player(db_unique_player_id, db_unique_server_id)

        player_inventory = await db.get_player_inventory(db_unique_player_id)
        essences = []
        common_flora = []
        specialty_items = []

        if not player:
            await interaction.followup.send(f"You don't have an inventory {str(interaction.user.display_name)}! Are you even a player?")
            return

        if not player_inventory:
            await interaction.followup.send(
                f"Your inventory is empty {player["character_name"]}! Go gather more stuff!")
            return

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

    @app_commands.command(
        name="transfer",
        description="Give inventory items to another player."
    )
    @app_commands.autocomplete(username=utils.player_autocompletion)
    @app_commands.autocomplete(component=utils.component_autocompletion)
    @app_commands.describe(username="Giving to?", component="Which item?", quantity="How much?")
    async def transfer(self, interaction, username: str, component: str, quantity: int):
        db_unique_server_id = await db.get_server_database_id(interaction.guild.id)
        owner_db_unique_player_id = await db.get_player_database_id(interaction.user.id, db_unique_server_id)
        owning_player = await db.get_player(owner_db_unique_player_id, db_unique_server_id)
        if not owning_player:
            await interaction.response.send_message(
                f"You don't have an inventory {str(interaction.user.display_name)}! What are you trying to give away?!")
            return

        owning_player_inventory = await db.get_player_inventory(owner_db_unique_player_id)
        owner_has_item, owner_amount = await utils.check_inventory(owning_player_inventory, component)

        target_player_display_name, target_player_db_unique_id, db_unique_server_id = await utils.split_player_autocomplete_return_value(username)

        target_player_character = await db.get_player(target_player_db_unique_id, db_unique_server_id)
        if target_player_db_unique_id == 0 or  db_unique_server_id == 0:
            await interaction.response.send_message(f"{target_player_display_name} is not a player.")
            return

        if response := await utils.validate_components(component, quantity):
            return await interaction.response.send_message(response)

        if not owner_has_item:
            await interaction.response.send_message(
                f"You do not have any {component} in your inventory, {interaction.user.display_name}! You should probably go get some more.")
            return

        if (owner_amount - quantity) < 0:
            await interaction.response.send_message(f"You don't have {quantity} {component} to transfer. Quit trying to cheat {interaction.user.display_name}!")
            return

        if (owner_amount - quantity) == 0:
            await db.delete_player_inventory_item(owner_db_unique_player_id, await utils.sanitize_input(component))
        else:
            await db.sub_player_inventory_item(owner_db_unique_player_id, await utils.sanitize_input(component), quantity)

        await db.add_player_inventory_item(target_player_db_unique_id, await utils.sanitize_input(component),quantity)
        await interaction.response.send_message(f"Successfully transferred {quantity} {component} to {target_player_character['character_name']}!")

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
    await bot.add_cog(PlayerCommands(bot))