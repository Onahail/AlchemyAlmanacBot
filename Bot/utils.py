"""Miscellaneous utility functions"""
import discord
import typing
import json
import math

from discord import app_commands

from db import db

with open('images.json', 'r') as file:
    images = json.load(file)


essence_names = ["Earth", "Fire", "Air", "Water", "Ice", "Lightning"]
common_flora_names = ["Alchemilla", "Deadly Nightshade", "Ephedra", "Fleshwort", "Juniper Berries", "Willow Bark"]
creature_bases = ['Aberrations', 'Celestials', 'Dragons', 'Fey', 'Fiends', 'Giants', 'Humanoids', 'Monstrosities', 'Oozes', 'Undead']


def has_role(role_name: str):
    async def predicate(interaction) -> bool:
        return any(role.name == role_name for role in interaction.user.roles)

    return app_commands.check(predicate)

async def get_image_url(item_name):
    for item in images:
        if item['name'] == item_name:
            return item['url']
    return None


async def recipe_to_string(
    recipe: tuple[tuple[dict[str, any], ...], ...],
    bullet: str = " • ",
    group_delimiter: str = "\n",
) -> str:
    """Converts raw recipe to nicely formatted string"""
    group_strings = []
    #recipe_name = recipe[0][0]['recipe']

    for group in recipe:
        group_string = bullet + ", ".join(
            [component["display_name"] for component in group[:-1]]
        )
        if len(group) > 2:
            group_string += ","
        if len(group) > 1:
            group_string += " or "

        group_string += f"{group[-1]["display_name"]} ({group[-1]["quantity"]})"
        group_strings.append(group_string)

    return group_delimiter.join(group_strings)


async def sanitize_input(input_string: str) -> str:
    """Sanitizes input for database access"""
    stripped = input_string.replace("-", " ")
    cleaned = ''.join(char for char in stripped if char.isalnum() or char.isspace())
    sanitized = ''.join(part.capitalize() for part in cleaned.split())

    return sanitized


async def get_role_color(interaction):
    """Grabs the role color for any custom role"""
    role_color = discord.Color.default()
    if interaction.user.roles:
        colored_roles = [role for role in sorted(interaction.user.roles, key=lambda r: r.position, reverse=True) if
                         role.color != discord.Color.default()]
        if colored_roles:
            role_color = colored_roles[0].color

    return role_color


async def check_inventory(player_inventory, component):
    """Checks if an item exists in players inventory"""
    quantity = None

    for item in player_inventory:
        if item["display_name"] == component:
            return True, item['quantity']

    return False, quantity


async def split_ingredients(recipe):
    """Splits ingredients out into primary and secondary components"""
    singular_ingredient = []
    swappable_ingredient = None
    swappable = False
    error = None
    recipe_name = recipe[0][0]['recipe']

    for component in recipe:
        if recipe_name == "DraughtOfGiantsStrength" or recipe_name == "DragonTea":
            if component[0]['display_name'] == "Giant Heartsblood" or component[0]['display_name'] == "Dragon Dust":
                swappable = True
                swappable_ingredient = component
        if len(component) > 1:
            swappable_ingredient = component
            swappable = True
        else:
            singular_ingredient.append(component)

    return singular_ingredient, swappable_ingredient, swappable, error


async def split_player_autocomplete_return_value(id_string: str) -> tuple:
    if "|" not in id_string:
        return id_string, 0, 0
    display_name, user_id_str, server_id_str = id_string.split("|")
    user_id = int(user_id_str)
    server_id = int(server_id_str)
    return display_name, user_id, server_id


async def get_display_name(interaction, user_id) -> str:
    member = interaction.guild.get_member(user_id)
    return member.display_name


async def component_autocompletion(interaction, current: str) -> typing.List[app_commands.Choice[str]]:
    data = []
    for component in db.components:
        if (component["display_name"].lower().startswith(current) or component["display_name"].startswith(current)) and len(data) < 25:
            data.append(app_commands.Choice(name=component["display_name"], value=component["display_name"]))
    return data


async def player_autocompletion(interaction, current: str) -> typing.List[app_commands.Choice[str]]:
    server_database_id = await db.get_server_database_id(interaction.guild.id)
    players = await db.get_all_players(server_database_id)
    data = []
    for player in players:
        display_name = await get_display_name(interaction, player["user_id"])
        if (display_name.lower().startswith(current) or display_name.startswith(current)) and len(data) < 25:
            data.append(app_commands.Choice(name=display_name, value=f"{display_name}|{player["id"]}|{server_database_id}"))
    return data


async def discord_member_autocompletion(interaction, current: str):
    data = []
    for member in interaction.guild.members:
        if not member.bot:
            if member.name.startswith(current) and len(data) < 25:
                data.append(app_commands.Choice(name=member.display_name, value=f"{member.display_name}|{member.id}"))
    return data


async def dm_autocompletion(interaction, current: str):
    server_database_id = await db.get_server_database_id(interaction.guild.id)
    dm = db.get_server_dm(server_database_id)
    data = []
    display_name = await get_display_name(interaction, dm["user_id"])
    if (display_name.lower().startswith(current) or display_name.startswith(current)) and len(data) < 25:
        data.append(app_commands.Choice(name=display_name, value=f"{display_name}|{dm["user_id"]}|{server_database_id}"))
    return data


async def craft_recipe_autocompletion(interaction, current: str) -> typing.List[app_commands.Choice[str]]:
    data = []
    craft_type = str(interaction.namespace.craft_type)

    if craft_type == "Medicine":
        for medicine in db.medicines:
            if (medicine["display_name"].lower().startswith(current) or medicine["display_name"].startswith(current)) and len(data) < 25:
                data.append(app_commands.Choice(name=medicine["display_name"], value=medicine["display_name"]))
    if craft_type == "Alchemy":
        for alchemical_item in db.alchemical_items:
            if (alchemical_item["display_name"].lower().startswith(current) or alchemical_item["display_name"].startswith(current)) and len(data) < 25:
                data.append(app_commands.Choice(name=alchemical_item["display_name"], value=alchemical_item["display_name"]))
    return data


async def find_available_ingredients(player_inventory, swappable_ingredients):
    """Returns any ingredients that the recipe requires that the player has"""
    inventory_dict = {item['display_name']: item['quantity'] for item in player_inventory}

    available_ingredients = []
    for item in swappable_ingredients:
        if item['display_name'] in inventory_dict:
            for _ in range(inventory_dict[item['display_name']]):
                available_ingredients.append(item)

    return tuple(available_ingredients)


async def type_autocompletion(interaction, current: str) -> typing.List[app_commands.Choice[str]]:
    crafting_types = ['Medicine', 'Alchemy']
    data = []
    for crafting_type in crafting_types:
        data.append(app_commands.Choice(name=crafting_type, value=crafting_type))
    return data


async def region_autocompletion(interaction, current: str) -> typing.List[app_commands.Choice[str]]:
    regions = db.regions
    data = []
    for region in regions:
        if region['name'].lower().startswith(current) or region['name'].startswith(current):
            data.append(app_commands.Choice(name=region['name'], value=region['name']))
    return data


async def creature_base_autocompletion(interaction, current: str) -> typing.List[app_commands.Choice[str]]:
    data = []
    for base in creature_bases:
        if base.lower().startswith(current) or base.startswith(current):
            data.append(app_commands.Choice(name=base, value=base))
    return data


async def creature_name_autocompletion(interaction, current: str) -> typing.List[app_commands.Choice[str]]:
    avail_creatures = await db.get_creatures_by_creature_base(str(interaction.namespace.base))
    data = []
    for creature in avail_creatures:
        data.append(app_commands.Choice(name=creature['creature_name'], value=creature['creature_name']))
    return data


async def common_table_autocompletion(interaction, current: str) -> typing.List[app_commands.Choice[str]]:
    common_tables = ['Essence','Flora']
    data = []
    for table in common_tables:
        data.append(app_commands.Choice(name=table, value=table))
    return data


async def split_list(lst):
    """Split a list into two columns. If the list is more than 9 items, split evenly with a minimum of 5 items on the right side."""
    if len(lst) <= 9:
        return lst, []
    else:
        split = len(lst) / 2
        split = math.ceil(split)
        return lst[:split], lst[split:]


async def validate_player_and_components(username, component, quantity):

    user_display_name, db_unique_player_id, db_unique_server_id = await split_player_autocomplete_return_value(
        username)
    if db_unique_player_id == 0 or db_unique_server_id == 0:
        return None, None, None, f"{username} is not a player."

    player = await db.get_player(db_unique_player_id, db_unique_server_id)
    if not player:
        return None, None, None, "That player doesn't have an inventory."

    if quantity < 0:
        return None, None, None, "Don't use negative numbers."

    if component not in [c["display_name"] for c in db.components]:
        return None, None, None, "That component doesn't exist."

    return user_display_name, db_unique_player_id, player, None


async def validate_components(component, quantity):
    if quantity < 0:
        return "Don't use negative numbers."

    if component not in [c["display_name"] for c in db.components]:
        return "That component doesn't exist."

