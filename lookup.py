import discord
import utils
import special_case_tables as sct

from discord import app_commands, Embed
from discord.ext import commands

from db import db


class Lookup(commands.GroupCog, group_name="lookup"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="recipe",
        description="Look up a specific recipe."
    )
    @app_commands.autocomplete(craft_type=utils.type_autocompletion)
    @app_commands.autocomplete(item_name=utils.craft_recipe_autocompletion)
    @app_commands.describe(craft_type="Which type?", item_name="Which item?")
    async def recipe(self, interaction, craft_type: str, item_name: str):
        await interaction.response.defer(thinking=True)
        role_color = await utils.get_role_color(interaction)

        #user_id = interaction.user.id
        #player = await db.get_player(user_id, server_id)

        if craft_type == 'Medicine':
            item = await db.get_medicine_recipe(await utils.sanitize_input(item_name))
        elif craft_type == 'Alchemy':
            item = await db.get_alchemy_recipe(await utils.sanitize_input(item_name))
        else:
            await interaction.followup.send("Invalid type specified. Please choose from Medicine, Alchemy")
            return

        title = "Recipe Book"

        embed = Embed(title=title, color=role_color)

        if item:
            name = item_name
            stats = None
            description = None
            special_requirements = None
            strength = None
            boostable = False
            #duration = "Test"
            #dice = "Test"
            #boost = "Test"
            if craft_type == "Alchemy":
                description = await db.get_alchemy_description(await utils.sanitize_input(item_name))
                special_requirements = await db.get_special_requirements(await utils.sanitize_input(item_name))
                strength = await db.get_alchemy_strength(await utils.sanitize_input(item_name))
            elif craft_type == "Medicine":
                description = await db.get_medicine_description(await utils.sanitize_input(item_name))
                strength = await db.get_medicine_strength(await utils.sanitize_input(item_name))
                stats = await db.get_medicine_stats(await utils.sanitize_input(item_name))
                if stats[0]["boost"]:
                    boostable = True

            item_recipe = await utils.recipe_to_string(item)

            embed = Embed(
                title=f"{name} {strength}",
                description=description,
                color=role_color)

            # TODO: Recipe check code
            # special_case_tables is imported as sct.
            item_table = False
            table_data = ""
            if name == "Dragon Tea":
                table_data = sct.dragon_tea_table
                item_table = True
            elif name == "Prismatic Balm":
                table_data = sct.prismatic_balm_table
                item_table = True
            elif name == "Draught of Giant's Strength":
                table_data = sct.giant_strength_table
                item_table = True
            elif name == "Mastermind":
                table_data = sct.mastermind_table
                item_table = True

            if item_table:
                embed.add_field(
                    name="",
                    value=table_data,
                    inline=False
                )

            embed.set_author(name="Recipe Book", icon_url='https://i.imgur.com/hPZLLLe.png')
            embed.set_thumbnail(url=await utils.get_image_url(item_name))

            embed.add_field(
                name=f"***Required Components:***",
                value=item_recipe,
                inline=True
            )

            if craft_type == "Medicine" and boostable:
                if stats[0]['boost']:
                    if stats[0]['boost'] == "Alchemilla":
                        boost_effect = "Duration"
                    elif stats[0]['boost'] == "Ephedra":
                        boost_effect = "Dice"

                details = (f"**Boost:** {stats[0]['boost'] if stats[0]['boost'] else "None"}\n"
                           f"**Boost Amount:** {stats[0]['boost_amt'] if stats[0]['boost_amt'] else "None"}\n"
                           f"**Boost Effects:** {boost_effect}\n")
                embed.add_field(
                    name="",
                    value=details,
                    inline=True
                )

            if special_requirements:
                embed.add_field(
                    name=f"***Special Requirements***",
                    value=special_requirements,
                    inline=False
                )

        else:
            name = "Recipe not found."
            embed.add_field(name=f"{name}", value="", inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="component",
        description="Retrieve detailed information on a specific component."
    )
    @app_commands.autocomplete(component=utils.component_autocompletion)
    @app_commands.describe(component="Which component?")
    async def component(self, interaction, component: str):
        await interaction.response.defer(thinking=True)
        role_color = await utils.get_role_color(interaction)
        component_source = await db.get_component_source(await utils.sanitize_input(component))
        component_info = await db.get_component_by_name(await utils.sanitize_input(component))

        component_description = component_info['description']
        source_type = component_source[0]['source_type']  # Creature, Region, CommonTable, Merchant
        amount = component_source[0]['amount']
        source_name = component_source[0]['source_name']
        source_details = component_source[0]['source_detail']
        roll = component_source[0]['roll']
        description = "None"

        embed = Embed(
            title=component,
            description=component_description,
            color=role_color)

        if source_type == "Creature":
            embed.set_author(name="Creature Codex", icon_url='https://i.imgur.com/hPZLLLe.png')

            description = (
                f"**Source**: {source_details} - {source_name}\n"
                f"**Amount**: {amount}\n"
                f"**DC**: {roll}"
            )

            footer_text = []

            if "+5" in roll:
                footer_text.append('+5 in DC means you can harvest this material again for every +5 over the base roll.')

            if amount == 'Δ':
                footer_text.append(
                    'Δ: Amount depends on the size of the creature as follows: Medium or smaller = 1; Large = 2; Huge = 4; Gargantuan or larger = 8.')

            if footer_text:
                embed.set_footer(text='\n'.join(footer_text))

        elif source_type == "Region":
            embed.set_author(name="Field Guide to Magical Flora", icon_url='https://i.imgur.com/hPZLLLe.png')
            regions = []
            for source in component_source:
                regions.append(source['source_name'])

            description = (
                f"**Source**: {", ".join(regions)}\n"
                f"**DC**: {roll}"
            )

        elif source_type == "CommonTable":
            embed.set_author(name="Field Guide to Magical Flora", icon_url='https://i.imgur.com/hPZLLLe.png')
            if source_name == "Flora":
                description = (
                    f"**Source**: Common Flora - All Regions\n"
                    f"**DC**: 10/+5\n"
                    f"**Table Roll**: {roll} on a D6"
                )
                embed.set_footer(
                    text="Minimum roll of 10 on a D20. Every +5 over that grants an additional roll. Use /lookup common_tables for a full printout of the Common Flora table."
                )

            elif source_name == "Essence":
                embed.set_author(name="Tome of Alchemical Energies", icon_url='https://i.imgur.com/hPZLLLe.png')

                description = (
                    f"**Source**: Elemental Essence - All Regions and All Creatures\n"
                    f"**DC**: 10/+5\n"
                    f"**Table Roll**: {roll} on a D6"
                )
                embed.set_footer(
                    text="Minimum roll of 10 on a D20. Every +5 over that grants an additional roll. Use /lookup common_tables for a full printout of the Essences table."
                )

        elif source_type == "Merchant":
            embed.set_author(name="Market Master's Guide", icon_url='https://i.imgur.com/hPZLLLe.png')

            description = (
                f"**Source**: Merchant\n"
                f"**Availability**: {source_details}\n"
                f"**Cost**: {amount}*"
            )
            embed.set_footer(
                text="*Suggested price and availability from the module. Both up to DM's discretion."
            )

        embed.add_field(
            name="",
            value=description,
            inline=False
        )

        medicines = []
        alchemy = []
        boosts = []

        recipes = await db.get_component_recipes(await utils.sanitize_input(component))
        boosted_medicines = await db.get_boosted_recipes_by_component(await utils.sanitize_input(component))
        for recipe in recipes:
            if recipe['medicine']:
                medicines.append(recipe['medicine'])
            if recipe['alchemy']:
                alchemy.append(recipe['alchemy'])

        for medicine in boosted_medicines:
            boosts.append(medicine['display_name'])




        if medicines:
            med_column1, med_column2 = await utils.split_list(medicines)
            med_column1 = "\n".join(med_column1)
            med_column2 = "\n".join(med_column2)

            embed.add_field(
                name="**Medicines**:",
                value=med_column1,
                inline=True
            )

            embed.add_field(
                name="\u200b",
                value=med_column2,
                inline=True
            )

        if alchemy:
            alch_column1, alch_column2 = await utils.split_list(alchemy)
            alch_column1 = "\n".join(alch_column1)
            alch_column2 = "\n".join(alch_column2)

            embed.add_field(
                name="**Alchemical Items**:",
                value=alch_column1,
                inline=True
            )

            embed.add_field(
                name="\u200b",
                value=alch_column2,
                inline=True
            )

        if boosts:
            boost_column1, boost_column2 = await utils.split_list(boosts)
            boost_column1 = "\n".join(boost_column1)
            boost_column2 = "\n".join(boost_column2)

            embed.add_field(
                name=f"**Boosts the {"Duration" if component == "Alchemilla" else "Dice Count"} of the following Medicines**:",
                value= boost_column1,
                inline=True
            )

            embed.add_field(
                name="\u200b",
                value=boost_column2,
                inline=True
            )

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="region",
        description="Retrieve information about a particular region."
    )
    @app_commands.autocomplete(name=utils.region_autocompletion)
    @app_commands.describe(name="Where you at?")
    async def region(self, interaction, name: str):
        await interaction.response.defer(thinking=True)
        color = await utils.get_role_color(interaction)
        region_info = await db.get_region_by_name(name)
        region_components = await db.get_components_by_region(name)
        component_name = []
        component_dc = []

        for comp in region_components:
            component_name.append(comp['display_name'])
            component_dc.append(comp['dc'])

        component_description = (f"Roll on the Essences table\n"
                                 f"Roll on the Common Flora table\n"
                                 f"{"\n".join(component_name)}")

        component_dc_description = (f"10/+5\n"
                                    f"10/+5\n"
                                    f"{"\n".join(component_dc)}")

        embed = Embed(
            title=name,
            description=region_info['description'],
            color=color
        )
        embed.set_author(name="Field Guide to Magical Flora", icon_url='https://i.imgur.com/hPZLLLe.png')



        embed.add_field(
            name=f"**Component**",
            value=component_description,
            inline=True
        )

        embed.add_field(
            name=f"Component DC",
            value=component_dc_description,
            inline=True
        )

        embed.set_thumbnail(url=region_info['image'])

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="creature",
        description="Retrieve harvesting information about a creature type."
    )
    @app_commands.autocomplete(base=utils.creature_base_autocompletion)
    @app_commands.autocomplete(name=utils.creature_name_autocompletion)
    @app_commands.describe(base="What'd you kill?", name="Specific type?")
    async def creature(self, interaction, base: str, name: str):
        color = await utils.get_role_color(interaction)
        creature_info = await db.get_creature_by_name(base, name)
        creature_components = await db.get_components_by_creature_name(base,name)
        component_name = []
        component_amount = []
        component_dc = []
        footer_text = []

        for comp in creature_components:
            component_name.append(comp['display_name'])
            component_amount.append(comp['amount'])
            component_dc.append(comp['dc'])

            footer_text.append("1. Check /how_to to determine which skill check is needed to harvest this creature. They're not all the same")

            if "+5" in comp['dc']:
                footer_text.append(
                    f"{len(footer_text) + 1}. +5 in DC means you can harvest this material again for every +5 over the base roll.")

            if comp['amount'] == 'Δ':
                footer_text.append(
                    f"{len(footer_text) + 1}. Δ: Amount depends on the size of the creature as follows: Medium or smaller = 1; Large = 2; Huge = 4; Gargantuan or larger = 8.")

        component_description = (f"Roll on the Essences table\n"
                                 f"{"\n".join(component_name)}")

        component_dc_description = (f"10/+5\n"
                                    f"{"\n".join(component_dc)}")

        component_amount_description = (f"1\n"
                                        f"{"\n".join(component_amount)}")

        embed = Embed(
            title=f"{base} - {name}",
            description=creature_info[0]['description'],
            color=color
        )
        embed.set_author(name="Creature Codex", icon_url='https://i.imgur.com/hPZLLLe.png')



        embed.add_field(
            name=f"**Component**",
            value=component_description,
            inline=True
        )

        embed.add_field(
            name="Amount",
            value=component_amount_description,
            inline=True
        )

        embed.add_field(
            name=f"Component DC",
            value=component_dc_description,
            inline=True
        )

        if footer_text:
            embed.set_footer(text='\n'.join(footer_text))


        #TODO Get images for creatures
        #embed.set_thumbnail(url=region_info['image'])

        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="common_tables",
        description="Display the common table for Essences and Common Flora"
    )
    @app_commands.autocomplete(table=utils.common_table_autocompletion)
    @app_commands.describe(table="Which table?")
    async def common_tables(self, interaction, table: str):
        await interaction.response.defer(thinking=True)
        color = await utils.get_role_color(interaction)
        display_table = await db.get_common_tables(table)
        title = "Error"
        roll = []
        component = []

        if table == "Essence":
            title = "Essences Table"
        elif table == "Flora":
            title = "Common Flora Table"

        for comp in display_table:
            roll.append(str(comp['roll']))
            component.append(comp['display_name'])

        embed = Embed(
            title=title,
            color=color
        )

        embed.add_field(
            name="D6",
            value=f"{"\n".join(roll)}",
            inline=True
        )

        embed.add_field(
            name="Component",
            value=f"{"\n".join(component)}"
        )

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
    await bot.add_cog(Lookup(bot))
