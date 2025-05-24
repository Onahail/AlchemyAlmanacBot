import discord
import utils

from discord import app_commands, Embed, ButtonStyle, SelectOption
from discord.ext import commands
from discord.ui import Button, View, Select

from db import db

class ComponentSelectMenu(Select):
    def __init__(self, swappable_components, minquantity, maxquantity):
        options = [
            SelectOption(label=component['display_name'], value=f"{component['display_name']}_{idx + 1}")
            for idx, component in enumerate(swappable_components)
        ]
        placeholder = f"Required Choices: {minquantity}" if not maxquantity else f"Optional Medicine Strength Boost: {minquantity-1}-{maxquantity}"
        super().__init__(placeholder=placeholder,
                         min_values=minquantity-1 if maxquantity else minquantity,
                         max_values=maxquantity if maxquantity else minquantity,
                         options=options)

    async def callback(self, interaction):
        if interaction.user.id != self.view.author_id:
            await interaction.response.send_message(
                f"Hands off {str(interaction.user.global_name)}! This isn't your dropdown!")
            return

        selected_options = [option for option in self.options if option.value in self.values]

        if selected_options is None:
            await interaction.response.send_message("No valid components were selected.", ephemeral=True)
            return

        if len(self.options) == 0:
            self.options = [SelectOption(label="Empty", value="Empty")]

        for selected_option in selected_options:
            self.view.chosen_components.append(selected_option.label)
            if hasattr(self.view, "maxquantity"):
                self.view.strength = "★ "+ self.view.strength

        if hasattr(self.view, "current_rank_stat"):
            self.view.current_rank_stat = self.view.rank_stats[len(selected_options)]

        self.disabled = True

        embed = await build_content_block(
            craft_type=self.view.craft_type,
            item_name=self.view.item_name,
            strength=self.view.strength,
            singular_ingredients=self.view.singular_components,
            swappable_ingredients=self.view.swappable_components,
            chosen_ingredients=self.view.chosen_components,
            boostable=self.view.boostable,
            boosts_available=self.view.boosts_available,
            selected_boosts=self.view.selected_boosts,
            boost_type=self.view.boost_type if hasattr(self.view, 'boost_type') else None,
            duration=self.view.duration if hasattr(self.view, 'duration') else None,
            dice=self.view.dice if hasattr(self.view, 'dice') else None,
            color=await utils.get_role_color(interaction),
            rank_title=self.view.rank_title if hasattr(self.view, 'rank_title') else None,
            rank_stats=self.view.current_rank_stat if hasattr(self.view, 'current_rank_stat') else None
        )

        await interaction.response.edit_message(embed=embed, view=self.view)


class CraftConfirm(Button):
    def __init__(self, label, item_name):
        super().__init__(label=label, style=ButtonStyle.green)

    async def callback(self, interaction):
        if interaction.user.id != self.view.author_id:
            await interaction.response.send_message(
                f"Don't click other peoples buttons {str(interaction.user.global_name)}!")
            return

        final_components = []
        db_unique_server_id = await db.get_server_database_id(interaction.guild.id)
        db_unique_player_id = await db.get_player_database_id(interaction.user.id, db_unique_server_id)
        player = await db.get_player(db_unique_player_id, db_unique_server_id)
        player_inventory = await db.get_player_inventory(db_unique_player_id)

        for component in self.view.singular_components:
            final_components.append(component[0]['display_name'])

        if self.view.swappable:
            for component in self.view.chosen_components:
                final_components.append(component)

        for component in final_components:

            _, amount = await utils.check_inventory(player_inventory, component)
            if amount - 1 <= 0:
                await db.delete_player_inventory_item(db_unique_player_id, await utils.sanitize_input(component))
            else:
                await db.sub_player_inventory_item(db_unique_player_id, await utils.sanitize_input(component), 1)

        if hasattr(self.view, "selected_boosts"):
            if self.view.selected_boosts > 0:
                _, amount = await utils.check_inventory(player_inventory, self.view.boost_type)
                if amount - self.view.selected_boosts <= 0:
                    await db.delete_player_inventory_item(db_unique_player_id, await utils.sanitize_input(self.view.boost_type))
                else:
                    await db.sub_player_inventory_item(db_unique_player_id, await utils.sanitize_input(self.view.boost_type), self.view.selected_boosts)

        for item in self.view.children:
            if isinstance(item, ComponentSelectMenu):
                if not item.disabled:
                    await interaction.response.send_message("Please select your ingredients.", ephemeral=True)
                    return

        embed = await build_content_block(
            craft_type=self.view.craft_type,
            item_name=self.view.item_name,
            strength=self.view.strength,
            singular_ingredients=self.view.singular_components,
            swappable_ingredients=self.view.swappable_components,
            chosen_ingredients=self.view.chosen_components,
            boostable=self.view.boostable,
            boosts_available=self.view.original_boosts,
            selected_boosts=self.view.selected_boosts,
            boost_type=self.view.boost_type if hasattr(self.view, 'boost_type') else None,
            duration=self.view.duration if hasattr(self.view, 'duration') else None,
            dice=self.view.dice if hasattr(self.view, 'dice') else None,
            color=await utils.get_role_color(interaction),
            rank_title=self.view.rank_title if hasattr(self.view, 'rank_title') else None,
            rank_stats=self.view.current_rank_stat if hasattr(self.view, 'current_rank_stat') else None,
            final_craft=True
        )

        embed.set_author(name=f"{player['character_name']} successfully crafted:", icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text="Remember to add it to your inventory!")

        await interaction.response.edit_message(embed=embed, view=None)


class ComponentReset(Button):
    def __init__(self, label):
        super().__init__(label=label, style=ButtonStyle.primary)

    async def callback(self, interaction):
        if interaction.user.id != self.view.author_id:
            await interaction.response.send_message(
                f"Don't click other people buttons {str(interaction.user.global_name)}!")
            return

        self.view.chosen_components.clear()
        self.view.selected_boosts = 0
        self.view.boosts_available = self.view.original_boosts
        self.view.strength = self.view.original_strength

        for item in self.view.children:
            if isinstance(item, ComponentSelectMenu):
                item.disabled = False
                item.options = [
                    SelectOption(label=component['display_name'], value=f"{component['display_name']}_{idx + 1}")
                    for idx, component in enumerate(self.view.swappable_components)
                ]
            if isinstance(item, Boost):
                item.disabled = False

        embed = await build_content_block(
            craft_type=self.view.craft_type,
            item_name=self.view.item_name,
            strength=self.view.original_strength,
            singular_ingredients=self.view.singular_components,
            swappable_ingredients=self.view.swappable_components,
            chosen_ingredients=self.view.chosen_components,
            boostable=self.view.boostable,
            boosts_available=self.view.original_boosts,
            selected_boosts=self.view.selected_boosts,
            boost_type=self.view.boost_type if hasattr(self.view, 'boost_type') else None,
            duration=self.view.original_duration if hasattr(self.view, 'duration') else None,
            dice=self.view.original_dice if hasattr(self.view, 'dice') else None,
            rank_title=self.view.rank_title if hasattr(self.view, 'rank_title') else None,
            rank_stats=self.view.original_rank_stat if hasattr(self.view, 'original_rank_stat') else None,
            color=await utils.get_role_color(interaction)
        )

        await interaction.response.edit_message(embed=embed, view=self.view)


class Boost(Button):
    def __init__(self, label):
        super().__init__(label=label, style=ButtonStyle.secondary, emoji='🔥')

    async def callback(self, interaction):

        if interaction.user.id != self.view.author_id:
            await interaction.response.send_message(
                f"Don't click other people buttons {str(interaction.user.global_name)}!")
            return

        current_strength = self.view.strength

        if '☆' in current_strength:
            current_strength = current_strength.replace('☆', '★', 1)
        elif '✧' in current_strength:
            current_strength = current_strength.replace('✧', '✦', 1)
        self.view.strength = current_strength

        self.view.selected_boosts += 1
        self.view.boosts_available -= 1
        if self.view.boosts_available <= 0:
            self.disabled = True

        if self.view.boost_type == "Alchemilla":
            self.view.duration = self.extend_duration(self.view.duration, self.view.can_infinite)
        if self.view.boost_type == "Ephedra":
            self.view.dice = self.increase_dice(self.view.original_dice, self.view.selected_boosts)

        embed = await build_content_block(
            craft_type=self.view.craft_type,
            item_name=self.view.item_name,
            strength=self.view.strength,
            singular_ingredients=self.view.singular_components,
            swappable_ingredients=self.view.swappable_components,
            chosen_ingredients=self.view.chosen_components,
            boostable = self.view.boostable,
            boosts_available=self.view.boosts_available,
            selected_boosts=self.view.selected_boosts,
            boost_type=self.view.boost_type if hasattr(self.view, 'boost_type') else None,
            duration=self.view.duration if hasattr(self.view, 'duration') else None,
            dice=self.view.dice if hasattr(self.view, 'dice') else None,
            rank_title=self.view.rank_title if hasattr(self.view, 'rank_title') else None,
            rank_stats=self.view.current_rank_stat if hasattr(self.view, 'current_rank_stats') else None,
            color=await utils.get_role_color(interaction)
        )

        await interaction.response.edit_message(embed=embed, view=self.view)

    @staticmethod
    def extend_duration(duration: str, can_infinite: int) -> str:
        duration_mapping = {
            "1 Minute": "10 Minutes",
            "10 Minutes": "1 Hour",
            "1 Hour": "8 Hours",
            "8 Hours": "24 Hours",
            "24 Hours": "Indefinite" if can_infinite else "24 hours"
        }
        return duration_mapping.get(duration, duration)  # Default to original if not in mapping

    @staticmethod
    def increase_dice(original_dice: str, boosts: int) -> str:
        if original_dice is None:
            return None

        dice_mapping = {
            "1d8": ["2d8", "4d8", "8d8"],
            "2d6": ["4d6", "8d6", "16d6"],
            "1d4 + 1": ["2d4 + 1", "4d4 + 1"]
        }

        if original_dice in dice_mapping and boosts <= len(dice_mapping[original_dice]):
            return dice_mapping[original_dice][boosts - 1]

        return original_dice


class CraftCancel(Button):
    def __init__(self, label):
        super().__init__(label=label, style=ButtonStyle.red)

    async def callback(self, interaction):

        if interaction.user.id != self.view.author_id:
            await interaction.response.send_message(
                f"Don't click other people buttons {str(interaction.user.global_name)}!")
            return

        await interaction.response.defer()
        await interaction.delete_original_response()


class CraftingView(View):
    def __init__(self, singular_components, swappable_components, item_name, strength, swappable, craft_type,
                 boosts_available, selected_boosts, boost_stats, ranked, author_id):
        super().__init__()

        self.author_id = author_id
        self.swappable = swappable
        self.chosen_components = []
        self.singular_components = singular_components
        self.swappable_components = swappable_components
        self.item_name = item_name
        self.strength = strength
        self.original_strength = strength
        self.boosts_available = boosts_available
        self.original_boosts = boosts_available
        self.craft_type = craft_type
        self.boostable = False

        if boost_stats:
            self.boost_type = boost_stats[0]['boost']
            if self.boost_type:
                self.boostable = True
            self.duration = boost_stats[0]['duration']
            self.original_duration = boost_stats[0]['duration']
            self.dice = boost_stats[0]['dice']
            self.original_dice = boost_stats[0]['dice']
            self.can_infinite = boost_stats[0]['can_infinite']
            self.selected_boosts = selected_boosts

        if ranked:
            self.rank_title = ranked[0]
            self.rank_stats = ranked[1:]
            self.original_rank_stat = ranked[1]
            self.current_rank_stat = ranked[1]

        if swappable:
            self.minquantity = swappable_components[0]['quantity']
            if craft_type == "Medicine":
                self.maxquantity = swappable_components[0]['rank_quantity']
            self.add_item(ComponentSelectMenu(
                swappable_components=swappable_components,
                minquantity=self.minquantity,
                maxquantity=self.maxquantity if hasattr(self, "maxquantity") else None))

        self.add_item(CraftConfirm(label="Confirm", item_name=item_name))
        if swappable:
            self.add_item(ComponentReset(label="Reset"))
        if craft_type == "Medicine" and self.boostable:
            boost_button = Boost(label="Boost")
            if self.boosts_available <= 0:
                boost_button.disabled = True
            self.add_item(boost_button)
        self.add_item(CraftCancel(label="Cancel"))


class Crafting(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="craft",
        description="Craft an item!"
    )
    @app_commands.autocomplete(item_name=utils.craft_recipe_autocompletion)
    @app_commands.autocomplete(craft_type=utils.type_autocompletion)
    async def craft(self, interaction, craft_type: str, item_name: str):
        db_unique_server_id = await db.get_server_database_id(interaction.guild.id)
        db_unique_player_id = await db.get_player_database_id(interaction.user.id, db_unique_server_id)
        stats = None
        ranked = None

        if craft_type == "Medicine":
            recipe = await db.get_medicine_recipe(await utils.sanitize_input(item_name))
            can_craft = await db.player_can_craft_medicine(db_unique_player_id, await utils.sanitize_input(item_name))
            strength = await db.get_medicine_strength(await utils.sanitize_input(item_name))
        elif craft_type == "Alchemy":
            recipe = await db.get_alchemy_recipe(await utils.sanitize_input(item_name))
            can_craft = await db.player_can_craft_alchemy(db_unique_player_id, await utils.sanitize_input(item_name))
            strength = await db.get_alchemy_strength(await utils.sanitize_input(item_name))
        else:
            await interaction.response.send_message("Please choose either Medicine or Alchemy.")
            return

        if strength == "★ ★ – ★ ★ ★ ★ ★":
            strength = "★ ★"
        elif strength == "★ ☆ – ★ ★ ★ ★ ☆":
            strength = "★ ☆"

        if can_craft:
            player_inventory = await db.get_player_inventory(db_unique_player_id)
            singular_ingredients, swappable_ingredients, swappable, error = await utils.split_ingredients(recipe)

            if error:
                await interaction.response.send_message(f"Error received: {error}")
                return
            available_ingredients = await utils.find_available_ingredients(player_inventory, swappable_ingredients) if swappable else None

            selected_boosts = 0
            boosts_available = 0
            boostable = False
            if craft_type == "Medicine":
                stats = await db.get_medicine_stats(await utils.sanitize_input(item_name))
                if stats:
                    if stats[0]['boost']:
                        boost_type = stats[0]['boost']
                        boostable = True
                        for item in player_inventory:
                            if item['display_name'] == boost_type:
                                if item['quantity'] < stats[0]['boost_amt']:
                                    boosts_available = item['quantity']
                                else:
                                    boosts_available = stats[0]['boost_amt']
                    if stats[0]['rank_values']:
                        ranked = stats[0]['rank_values'].split(",")
                        ranked = [i for i in ranked]

            embed = await build_content_block(
                craft_type=craft_type,
                item_name=item_name,
                strength=strength,
                singular_ingredients=singular_ingredients,
                swappable_ingredients=available_ingredients,
                chosen_ingredients=[],
                boostable=boostable,
                boosts_available=boosts_available,
                selected_boosts=selected_boosts,
                boost_type=stats[0]['boost'] if stats else None,
                duration=stats[0]['duration'] if stats else None,
                dice=stats[0]['dice'] if stats else None,
                rank_title=ranked[0] if ranked else None,
                rank_stats=ranked[1] if ranked else None,
                color=await utils.get_role_color(interaction)
            )

            view = CraftingView(
                singular_components=singular_ingredients,
                swappable_components=available_ingredients,
                item_name=item_name,
                strength=strength,
                swappable=swappable,
                craft_type=craft_type,
                boosts_available=boosts_available,
                selected_boosts=selected_boosts,
                boost_stats=stats if stats else None,
                ranked=ranked if ranked else None,
                author_id=interaction.user.id
            )

            await interaction.response.send_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(f"You do not have the required components to craft {item_name}.", ephemeral=True)

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


async def build_content_block(
        craft_type,
        item_name,
        strength,
        singular_ingredients,
        swappable_ingredients,
        chosen_ingredients,
        boostable,
        boosts_available,
        selected_boosts,
        boost_type,
        duration,
        dice,
        color,
        rank_title,
        rank_stats,
        final_craft=False
) -> Embed:

    embed = Embed(title=f"{item_name} {strength}", color=color)
    embed.set_author(name="Crafting Table", icon_url='https://i.imgur.com/3mauIj6.png')
    embed.set_image(url='https://i.imgur.com/IfBmnOp.png')

    boost_ingredient_line = f"**Boost Ingredient**: {boost_type}"
    boost_used_line = f"**Boost Used**: {'None' if selected_boosts == 0 
                                        else boost_type if boosts_available == 1 
                                        else boost_type + ' x' + str(selected_boosts)}"
    boosts_line = f"**Boosts Available:** {boosts_available}"
    duration_line = f"**Duration:** {duration}"
    dice_line = f"**Dice:** {dice}"
    rank_line = f"**{rank_title}:** {rank_stats}"

    details_lines = []

    if boostable:
        if not final_craft:
            if boost_ingredient_line:
                details_lines.append(boost_ingredient_line)
            if boosts_line:
                details_lines.append(boosts_line)
        else:
            details_lines.append(boost_used_line)
    if duration:
        details_lines.append(duration_line)
    if dice:
        details_lines.append(dice_line)
    if rank_title:
        details_lines.append(rank_line)

    details = "\n".join(details_lines)
    singular_ingredients_str = "\n".join([f"• {ingredient[0]['display_name']}" for ingredient in singular_ingredients])
    if swappable_ingredients:
        chosen_counts = {}
        for ingredient in chosen_ingredients:
            if ingredient in chosen_counts:
                chosen_counts[ingredient] += 1
            else:
                chosen_counts[ingredient] = 1
        chosen_str = "\n".join([f"• {ingredient} x{count}" if count > 1 else f"• {ingredient}" for ingredient, count in chosen_counts.items()])

    if singular_ingredients and not swappable_ingredients:
        embed.add_field(name="Singular Ingredients:", value=singular_ingredients_str, inline=True)
        embed.add_field(name="", value=details, inline=True)

    if not singular_ingredients and swappable_ingredients:
        embed.add_field(name="Chosen Ingredient(s):", value=f"{chosen_str}", inline=True)
        embed.add_field(name="", value=details, inline=True)

    if swappable_ingredients and singular_ingredients:
        embed.add_field(name="Singular Ingredients:", value=singular_ingredients_str, inline=True)
        embed.add_field(name="", value=details, inline=True)
        embed.add_field(name="Chosen ingredient(s):", value=f"{chosen_str}", inline=False)

    if final_craft:
        embed.set_image(url=await utils.get_image_url(item_name))
    else:
        embed.set_thumbnail(url=await utils.get_image_url(item_name))

    return embed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Crafting(bot))