import os

import discord
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1156597024641273939

RANK_NAME_TO_ROLE_NAME = {
    # "GUILD RANK NAME": "DISCORD ROLE NAME"
    "Veteran": "Veterans",
    "Raider": "Raiders",
    "Trial": "Trials",
    "Social": "Socials",
}

ROLE_NAME_TO_ROLE_ID = {
    # "DISCORD ROLE NAME": "DISCORD ROLE ID"
    "Veterans": 1397686990882738227,
    "Raiders": 1309183435851436142,
    "Trials": 1309183538842697809,
    "Socials": 1314598101184417895,
}

intents = discord.Intents.default()
intents.members = True

client = discord.Client(intents=intents)


async def set_guild_rank(user_id: int, rank_name: str) -> None:
    # Get the Discord server (guild) from the pre-defined Server ID.
    guild = client.get_guild(GUILD_ID)
    if guild is None:
        raise RuntimeError(f"Guild {GUILD_ID} not found")

    # Get the Discord user from the input argument.
    member = guild.get_member(user_id)
    if member is None:
        member = await guild.fetch_member(user_id)

    # Get the Discord role name from the input argument and the pre-defined list RANK_NAME_TO_ROLE_NAME.
    # This is only used temporarily before later being converted to a Discord role ID.
    role_name = RANK_NAME_TO_ROLE_NAME.get(rank_name)
    if role_name is None:
        valid_ranks = ", ".join(RANK_NAME_TO_ROLE_NAME.keys())
        raise ValueError(f"Unknown rank '{rank_name}'. Valid ranks: {valid_ranks}")

    # Convert the Discord role name to a Discord role ID.
    target_role_id = ROLE_NAME_TO_ROLE_ID.get(role_name)
    if target_role_id is None:
        raise RuntimeError(f"Role name '{role_name}' has no configured role ID")

    # Convert the Discord role ID to an object.
    target_role = guild.get_role(target_role_id)
    if target_role is None:
        raise RuntimeError(
            f"Role ID {target_role_id} for rank '{rank_name}' was not found"
        )

    # Create a list of roles to be removed from the Discord user and store it in roles_to_remove.
    # Managed roles are pre-defined in ROLE_NAME_TO_ROLE_ID.
    # The list is built from all managed roles the Discord user currently has, excluding the target role to be added.
    managed_role_ids = set(ROLE_NAME_TO_ROLE_ID.values())
    roles_to_remove = [
        role
        for role in member.roles
        if role.id in managed_role_ids and role.id != target_role.id
    ]

    if roles_to_remove:
        await member.remove_roles(*roles_to_remove, reason="Guild rank sync")

    if target_role not in member.roles:
        await member.add_roles(target_role, reason="Guild rank sync")
        print(f"Assigned role '{target_role.name}' to {member.display_name}")
    else:
        print(f"{member.display_name} already has role '{target_role.name}'")


@client.event
async def on_ready() -> None:
    print(f"Bot connected as {client.user}")


client.run(TOKEN)
