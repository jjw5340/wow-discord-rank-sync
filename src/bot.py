"""
Create the Discord client and provide helper functions for guild-rank syncing.
"""

from __future__ import annotations

import os

import discord
from dotenv import load_dotenv

from src.rank_roles import (
    get_managed_role_ids,
    get_rank_role_by_guild_rank,
)

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not DISCORD_BOT_TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN is not set")

discord_guild_id_raw = os.getenv("DISCORD_GUILD_ID")
if not discord_guild_id_raw:
    raise RuntimeError("DISCORD_GUILD_ID is not set")

try:
    DISCORD_GUILD_ID = int(discord_guild_id_raw)
except ValueError:
    raise RuntimeError("DISCORD_GUILD_ID must be an integer")

intents = discord.Intents.default()
intents.members = True

client = discord.Client(intents=intents)


async def set_guild_rank(user_id: int, rank_name: str) -> None:
    guild = client.get_guild(DISCORD_GUILD_ID)
    if guild is None:
        raise RuntimeError(f"Guild {DISCORD_GUILD_ID} not found")

    member = guild.get_member(user_id)
    if member is None:
        member = await guild.fetch_member(user_id)

    rank_role = get_rank_role_by_guild_rank(rank_name)
    if rank_role is None:
        raise ValueError(f"Unknown rank {rank_name!r}")

    target_role = guild.get_role(rank_role.discord_role_id)
    if target_role is None:
        raise RuntimeError(
            f"Role ID {rank_role.discord_role_id} for rank {rank_name!r} was not found"
        )

    managed_role_ids = get_managed_role_ids()
    roles_to_remove = [
        role for role in member.roles
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


if __name__ == "__main__":
    client.run(DISCORD_BOT_TOKEN)
