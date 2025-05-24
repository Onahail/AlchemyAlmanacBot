import discord

from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select


class IndexDropdown(View):
    def __init__(self, embeds, author_id):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.embeds = embeds
        self.current_page = 0
        self.add_index_dropdown()

    def add_index_dropdown(self):
        options = [
            discord.SelectOption(label=embed.title, value=str(idx))
            for idx, embed in enumerate(self.embeds)
        ]
        self.dropdown = Select(placeholder=self.embeds[self.current_page].title, options=options, custom_id="index_dropdown")
        self.dropdown.callback = self.dropdown_callback
        self.add_item(self.dropdown)

    async def dropdown_callback(self, interaction):
        if interaction.user.id != self.author_id:
            await interaction.followup.send(
                f"Don't click other people's dropdowns, {str(interaction.user.global_name)}!", ephemeral=True)
            return
        self.current_page = int(interaction.data["values"][0])
        self.dropdown.placeholder = self.embeds[self.current_page].title
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)


class AlchemyGuide(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="how_to",
        description="Quick reference for creating potions and using alchemical items."
    )
    async def alchemy_guide(self, interaction):
        await interaction.response.defer(ephemeral=True)
        embeds = []

        # Page 1: Introduction
        embed_intro = discord.Embed(
            title="Introduction",
            description="Quick rules reference for creating potions and using alchemical items.",
            color=discord.Color.green()
        )
        embed_intro.add_field(
            name="How to Use Potions",
            value=(
                "**Drinking/Administering:** To use a potion, you typically need to spend an action, unless stated otherwise in the potion's description. The effects of the potion take place immediately upon consumption, and the potion is consumed in the process. The duration of the potion's effects will be specified in its description.\n\n"
                "**Combining Potions:** The rules for combining potions follow the general guidelines for combining game or magical effects. However, variant rules can be used for mixing potions to create unique effects.\n\n"
                "**Potions as Magic Items:** Most potions are considered magical and will count as such for any antimagic effects. However, some herbal medicines and certain adventuring equipment may be nonmagical, as determined by the GM.\n\n"
                "**Dispel Magic and Potions:** The dispel magic spell can be used to remove spell effects created by potions, but it does not work on the potion itself. Non-spell-based effects of potions are not affected by dispel magic."
            ),
            inline=False
        )
        embeds.append(embed_intro)

        embed_setup = discord.Embed(
            title="Setup",
            description="Before crafting or using potions, here's how to prepare your server and character.",
            color=discord.Color.blue()
        )

        embed_setup.add_field(
            name="🔑 Assigning a Dungeon Master (Admin-only)",
            value=(
                "Use `/register dm` to assign a Dungeon Master for your server.\n"
                "Only one DM is allowed per server. Admin permissions are required to run this command.\n"
                "To remove the DM, use `/deregister dm`."
            ),
            inline=False
        )

        embed_setup.add_field(
            name="🎭 Registering Players (DM-only)",
            value=(
                "The DM can register players using `/register player <user> <character name>`.\n"
                "This creates the player's inventory and character profile.\n"
                "To remove a player, use `/deregister player`."
            ),
            inline=False
        )
        embeds.append(embed_setup)

        embed_commands = discord.Embed(
            title="Command Reference",
            description="List of available commands by role.",
            color=discord.Color.teal()
        )

        embed_commands.add_field(
            name="📦 Inventory Management (DM-only)",
            value=(
                "• `/dm add` – Add components to a player's inventory\n"
                "• `/dm sub` – Remove components from a player's inventory\n"
                "• `/dm inventory` – View a player's inventory\n"
                "• `/dm list` – View all registered players"
            ),
            inline=False
        )

        embed_commands.add_field(
            name="🙋 Player Commands",
            value=(
                "• `/inventory` – View your own inventory\n"
                "• `/add` – Add a component to your inventory\n"
                "• `/sub` – Remove a component from your inventory\n"
                "• `/transfer` – Transfer components to another player\n"
                "• `/available_crafts` – View craftable recipes with your current inventory\n"
                "• `/craft` – Access the crafting table to make your items and medicines"
            ),
            inline=False
        )

        embed_commands.add_field(
            name="🔎 Lookup Tools (For Everyone)",
            value=(
                "• `/lookup recipe <name>` – View recipe details\n"
                "• `/lookup component <name>` – Learn about a crafting component\n"
                "• `/lookup creature <name>` – View creature drop info\n"
                "• `/lookup region <name>` – See what flora grows where\n"
                "• `/lookup common_tables <type>` – Roll on generic common component tables"
            ),
            inline=False
        )

        embeds.append(embed_commands)

        # Page 2: New Terminology
        embed_terminology = discord.Embed(
            title="New Terminology",
            color=discord.Color.green()
        )
        embed_terminology.add_field(
            name="Burning",
            value=(
                "Burning is a condition that inflicts fire damage at the start of each turn. The damage amount is specified in parentheses. While burning, the creature emits bright light in a 20-foot radius and dim light for an additional 20 feet. If a creature is subjected to multiple sources of burning, only the highest damage source applies. Burning ends if the creature takes an action to douse the flames or if it is fully immersed in water. Burning can also be cured by spells that heal diseases or poisons. Fire-immune creatures are also immune to burning."
            ),
            inline=False
        )
        embed_terminology.add_field(
            name="Extended Rest",
            value="An extended rest is a period of downtime that lasts at least one week. Certain potions require an extended rest before a character can benefit from them again.",
            inline=False
        )
        embed_terminology.add_field(
            name="Adjusting Prices",
            value=(
                "The costs for potions and alchemical items are based on playtesting and official rules. However, the GM can adjust prices based on the campaign's economy. The Total Party Income table helps align the game with expected gold earnings per level, allowing for adjustments such as doubling or halving prices."
            ),
            inline=False
        )
        embeds.append(embed_terminology)

        # Page 3: Gathering Plants
        embed_gathering = discord.Embed(
            title="Gathering Plants",
            color=discord.Color.green()
        )
        embed_gathering.add_field(
            name="Wilderness Areas",
            value=(
                "Gathering plants is an activity done in the wilderness. Suitable terrains include arctic, coast, desert, forest, grassland, mountain, swamp, and underground areas. It is not possible to gather plants in urban environments."
            ),
            inline=False
        )
        embed_gathering.add_field(
            name="Process",
            value=(
                "Gathering plants takes 1 hour and can be performed during a rest or while traveling. An Intelligence (Nature) check is required, with advantages if the character has proficiency in Nature and uses an herbalism kit. The result of the check determines the components gathered based on the terrain tables found using `/lookup terrain`."
            ),
            inline=False
        )
        embed_gathering.add_field(
            name="Spell Assisted Gathering",
            value=("Magic can be used in the following ways to assist in locating and harvesting of useful flora:\n"
                   "• When you cast locate animals or plants and name a useful plant or essence, the next time you make an Intelligence (Nature) check to locate useful plants while in the area revealed by the spell, the component DC of the chosen plant is reduced by 5 for that check. If you name a common plant or elemental essence, the DC for rolling on the corresponding table becomes 5/+5 for the check, instead of 10/+5.\n"
                   "• You can command a sprite or pixie under your control to gather useful flora on your behalf, with an attempt taking 1 hour as normal. For this purpose, the summoned creature is considered proficient in the Nature skill. Such creatures can be summoned with a conjure woodland beings spell or similar magic.\n"
                   "• Whenever you harvest a component while gathering in an area of land enriched by a plant growth spell, you can collect two units")
        )
        embeds.append(embed_gathering)

        # Page 4: Harvesting Creatures
        embed_harvesting = discord.Embed(
            title="Harvesting Creatures",
            color=discord.Color.green()
        )
        embed_harvesting.add_field(
            name="Requirements",
            value=(
                "A character that is proficient with and in possession of a harvesting kit can attempt to harvest useful components from a creature or a corpse, with proficiency representing the basic competence needed to wield the tools effectively. If the target isn’t dead, it must be incapacitated for the duration of any attempt to harvest components from it or the attempt fails. "
            ),
            inline=False
        )
        embed_harvesting.add_field(
            name="Process",
            value="Once the requirements are met, you can attempt to harvest useful components from your target. Each attempt takes 5 minutes or longer (determined by the GM), which can be performed during a short or long rest. At the end of the period, make a harvesting check using your harvesting kit. "
                  "If you or a creature helping you is proficient in the skill associated with the target’s type (shown in the Creature Harvesting table), you gain advantage on the check. Furthermore, if you or a creature helping you has the Favored Enemy class feature and the target is a favored enemy, you gain a +2 bonus to the check. "
                  "Temporary modifiers and other effects (such as Bardic Inspiration and effects that grant advantage) don’t apply to this check, nless they applied for the duration of the harvesting attempt.\n"
                  "Successful harvesting yields components according to the harvesting index found using `/lookup creature`. Proper storage in containers from a harvesting or alchemist kit is necessary to prevent spoilage.",
            inline=False
        )
        embed_harvesting.add_field(
            name="Creature Harvesting Skills",
            value=(
                "**Arcana:** Aberrations, Elementals, Fey\n"
                "**Survival:** Beasts, Dragons, Monstrosities\n"
                "**Religion:** Celestials, Fiends, Undead\n"
                "**Investigation:** Constructs\n"
                "**Medicine:** Giants, Humanoids\n"
                "**Nature:** Oozes, Plants"
            ),
            inline=False
        )
        embeds.append(embed_harvesting)

        # Page 5: Tools for Alchemy
        embed_tools = discord.Embed(
            title="Tools for Alchemy",
            color=discord.Color.green()
        )
        embed_tools.add_field(
            name="Herbalism Kit",
            value=(
                "An herbalism kit includes clippers, a mortar and pestle, pouches, and vials. Proficiency with this kit allows you to add your proficiency bonus to any ability checks you make to identify or apply herbs. Additionally, it lets you create antitoxin and potions of healing."
            ),
            inline=False
        )
        embed_tools.add_field(
            name="Alchemist's Supplies",
            value=(
                "Alchemist's supplies include two glass beakers, a metal frame to hold a beaker in place over an open flame, a glass stirring rod, a small mortar and pestle, and pouches of common alchemical ingredients. Proficiency with these supplies allows you to add your proficiency bonus to any ability checks you make to identify or create potions."
            ),
            inline=False
        )
        embed_tools.add_field(
            name="Harvesting Kit",
            value=(
                "A harvesting kit includes various tools for extracting components from creatures, such as knives, pliers, and small saws. Proficiency with this kit allows you to add your proficiency bonus to any ability checks you make to harvest components from creatures."
            ),
            inline=False
        )
        embed_tools.add_field(
            name="Activity",
            value=("Identify a creature, including any unusual characteristics or markings\n"
                   "Determine time of death"),
            inline=True
        )
        embed_tools.add_field(
            name="DC",
            value=("10\n"
                   "\u200b\n"
                   "20"),
            inline=True
        )
        embeds.append(embed_tools)

        # Page 6: Identifying Components
        embed_identifying = discord.Embed(
            title="Identifying Components",
            color=discord.Color.green()
        )
        embed_identifying.add_field(
            name="Using Skills to Identify",
            value=(
                "When you encounter an unknown component, you can attempt to identify it using the appropriate skill based on the component's type. For example, Arcana for magical components, Nature for plant-based components, etc. An Intelligence check using the appropriate skill can reveal information about the component's properties and potential uses."
            ),
            inline=False
        )
        embed_identifying.add_field(
            name="Using Tools to Identify",
            value=(
                "Proficiency with certain tools, such as an herbalism kit or alchemist's supplies, can also aid in identifying components. Using these tools grants you advantage on the Intelligence check to identify the component."
            ),
            inline=False
        )
        embed_identifying.add_field(
            name="Recording Information",
            value=(
                "Keep a journal or log of identified components and their uses. This can be a valuable resource for future reference and can help in quickly identifying components in the future."
            ),
            inline=False
        )
        embeds.append(embed_identifying)

        # Page 7: Storing Components
        embed_storage = discord.Embed(
            title="Storing Components",
            color=discord.Color.green()
        )
        embed_storage.add_field(
            name="Proper Storage",
            value=(
                "Proper storage of components is essential to prevent spoilage and maintain their potency. Components should be stored in airtight containers and kept in a cool, dry place. Some components may require special storage conditions, such as being kept in a dark place or submerged in liquid."
            ),
            inline=False
        )
        embed_storage.add_field(
            name="Using Preservation Methods",
            value=(
                "Preservation methods, such as drying, salting, or using preservatives, can extend the shelf life of components. These methods can be applied using an herbalism kit or alchemist's supplies."
            ),
            inline=False
        )
        embed_storage.add_field(
            name="Labeling and Cataloging",
            value=(
                "Clearly label and catalog all stored components. Include information such as the component's name, date of collection, and any special storage requirements. This helps in keeping track of your inventory and ensures that you use the oldest components first."
            ),
            inline=False
        )
        embeds.append(embed_storage)

        # Page 8: Creating Potions
        embed_potions = discord.Embed(
            title="Creating Potions",
            color=discord.Color.green()
        )
        embed_potions.add_field(
            name="Gathering Ingredients",
            value=(
                "Gather the necessary ingredients as specified in the potion recipe. These ingredients can be gathered from the wilderness or harvested from creatures as outlined in the previous sections."
            ),
            inline=False
        )
        embed_potions.add_field(
            name="Using an Alchemist's Kit",
            value=(
                "An alchemist's kit is required to create potions. Proficiency with this kit allows you to add your proficiency bonus to any ability checks made to create potions. The process typically involves combining the ingredients in the correct proportions and using alchemical techniques to brew the potion."
            ),
            inline=False
        )
        embed_potions.add_field(
            name="Brewing Time",
            value=(
                "The time required to brew a potion varies depending on its complexity. Simple potions may take a few hours, while more complex potions can take several days. The brewing time is specified in the potion recipe."
            ),
            inline=False
        )
        embed_potions.add_field(
            name="Quality Control",
            value=(
                "During the brewing process, make periodic checks to ensure the potion is developing correctly. These checks can be Intelligence (Arcana) or Wisdom (Medicine) checks, depending on the nature of the potion. Success ensures a high-quality potion, while failure may result in a flawed or unstable potion."
            ),
            inline=False
        )
        embeds.append(embed_potions)

        view = IndexDropdown(embeds=embeds, author_id=interaction.user.id)
        await interaction.followup.send(embed=embeds[0], view=view, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AlchemyGuide(bot))