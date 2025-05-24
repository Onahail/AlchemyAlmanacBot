import discord
import utils
import json

from discord import app_commands, Embed, Interaction, ButtonStyle
from discord.ext import commands
from discord.ui import Button, View, button

from db import db

with open('images.json', 'r') as file:
    images = json.load(file)

class PaginatedView(View):
    def __init__(self, embeds, author_id):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.embeds = embeds
        self.current_page = 0
        self.update_buttons()

    def update_buttons(self):
        self.previous.disabled = self.current_page == 0
        self.next.disabled = self.current_page == len(self.embeds) - 1

    @button(label="Previous", style=ButtonStyle.secondary)
    async def previous(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.followup.send(
                f"Don't click other people buttons {str(interaction.user.global_name)}!")
            return
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @button(label="Next", style=ButtonStyle.secondary)
    async def next(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.followup.send(
                f"Don't click other people buttons {str(interaction.user.global_name)}!")
            return
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    @button(label="Close", style=ButtonStyle.red)
    async def close(self, interaction: Interaction, button: Button):
        if interaction.user.id != self.author_id:
            await interaction.followup.send(
                f"Don't click other people buttons {str(interaction.user.global_name)}!")
            return
        await interaction.response.defer(thinking=True)
        await interaction.delete_original_response()


class StandardView(View):
    def __init__(self, author_id):
        self.author_id = author_id
        super().__init__(timeout=None)

    @button(label="Close", style=ButtonStyle.red)
    async def close(self, interaction: Interaction, button: Button):
        await interaction.response.defer(thinking=True)
        if interaction.user.id != self.author_id:
            await interaction.followup.send(
                f"Don't click other people buttons {str(interaction.user.global_name)}!")
            return

        await interaction.delete_original_response()


class AvailableCrafts(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="available_crafts",
        description="Show available items to craft."
    )
    @app_commands.describe(craft_type="Medicine or Alchemical Item?")
    @app_commands.autocomplete(craft_type=utils.type_autocompletion)
    async def available_crafts(self, interaction, craft_type: str):
        await interaction.response.defer(ephemeral=True)
        role_color = await utils.get_role_color(interaction)

        db_unique_server_id = await db.get_server_database_id(interaction.guild.id)
        db_unique_player_id = await db.get_player_database_id(interaction.user.id, db_unique_server_id)
        player = await db.get_player(db_unique_player_id, db_unique_server_id)

        if craft_type == 'Medicine':
            items = await db.get_player_possible_medicines(db_unique_player_id)
            title = "Available Medicines"
        elif craft_type == 'Alchemy':
            items = await db.get_player_possible_alchemy(db_unique_player_id)
            title = "Available Alchemical Items"
        else:
            await interaction.followup.send("Invalid type specified. Please choose from Medicine, Alchemy")
            return

        view = StandardView(interaction.user.id)

        if items:
            embeds = await create_embeds(interaction, title, items)

            if len(embeds) > 1:
                view = PaginatedView(embeds, interaction.user.id)
                await interaction.followup.send(embed=embeds[0], view=view)
            else:
                await interaction.followup.send(embed=embeds[0], view=view)
        else:
            embed = Embed(title=title, color=role_color)
            embed.set_author(name=player["character_name"], icon_url=interaction.user.display_avatar.url)
            embed.add_field(name="No available items to craft.", value="", inline=False)
            await interaction.followup.send(embed=embed, view=view)

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


async def create_embeds(interaction,title, items, items_per_embed=4):
    embeds = []
    db_unique_server_id = await db.get_server_database_id(interaction.guild.id)
    db_unique_player_id = await db.get_player_database_id(interaction.user.id, db_unique_server_id)
    player = await db.get_player(db_unique_player_id,db_unique_server_id)
    for i in range(0, len(items), items_per_embed):
        embed = Embed(title=title, color=await utils.get_role_color(interaction))
        embed.set_author(name=f"{player['character_name']}'s Inventory")
        embed.set_thumbnail(url='https://i.imgur.com/M61wD5l.png')
        for item in items[i:i + items_per_embed]:
            name = f"{item['display_name']} {item['strength']}"
            description = item['description']
            special_requirements = item.get('special_requirements')
            max_crafts = item['max_crafts']
            recipe = await utils.recipe_to_string(item.get('recipe'))
            value = f"{description}\n*- Required Components:* {recipe}"

            if special_requirements:
                value = f"{description}\n*- Special Requirements:* `{special_requirements}`\n*- Required Components:* {recipe}"

            embed.add_field(
                name=f"{name} (Max Crafts: {int(max_crafts)})",
                value=value,
                inline=False
            )
        embeds.append(embed)
    return embeds


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AvailableCrafts(bot))