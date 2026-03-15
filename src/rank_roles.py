"""
Define guild-rank to Discord-role mappings and related helper functions.

This module is the single source of truth for:
- guild rank names
- Discord role names
- Discord role IDs
- whether a role is managed by the bot

The order of RANK_ROLES is significant and should be maintained from
highest rank to lowest rank.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RankRole:
    guild_rank: str
    discord_role_name: str
    discord_role_id: int
    managed_role: bool


RANK_ROLES: list[RankRole] = [
    RankRole(
        guild_rank="Officer",
        discord_role_name="Officers",
        discord_role_id=1163523170318426262,
        managed_role=False,
    ),
    RankRole(
        guild_rank="Veteran",
        discord_role_name="Veterans",
        discord_role_id=1397686990882738227,
        managed_role=True,
    ),
    RankRole(
        guild_rank="Raider",
        discord_role_name="Raiders",
        discord_role_id=1309183435851436142,
        managed_role=True,
    ),
    RankRole(
        guild_rank="Trial",
        discord_role_name="Trials",
        discord_role_id=1309183538842697809,
        managed_role=True,
    ),
    RankRole(
        guild_rank="Social",
        discord_role_name="Socials",
        discord_role_id=1314598101184417895,
        managed_role=True,
    ),
]


def get_rank_role_by_guild_rank(guild_rank: str) -> RankRole | None:
    """Return the RankRole matching a guild rank, or None if not found."""
    for rank_role in RANK_ROLES:
        if rank_role.guild_rank == guild_rank:
            return rank_role
    return None


def get_rank_role_by_discord_role_name(discord_role_name: str) -> RankRole | None:
    """Return the RankRole matching a Discord role name, or None if not found."""
    for rank_role in RANK_ROLES:
        if rank_role.discord_role_name == discord_role_name:
            return rank_role
    return None


def get_rank_role_by_discord_role_id(discord_role_id: int) -> RankRole | None:
    """Return the RankRole matching a Discord role ID, or None if not found."""
    for rank_role in RANK_ROLES:
        if rank_role.discord_role_id == discord_role_id:
            return rank_role
    return None


def get_managed_rank_roles() -> list[RankRole]:
    """Return the subset of rank roles that are managed by the bot."""
    return [rank_role for rank_role in RANK_ROLES if rank_role.managed_role]


def get_unmanaged_rank_roles() -> list[RankRole]:
    """Return the subset of rank roles that are not managed by the bot."""
    return [rank_role for rank_role in RANK_ROLES if not rank_role.managed_role]


def get_managed_role_names() -> list[str]:
    """Return managed Discord role names in hierarchy order."""
    return [rank_role.discord_role_name for rank_role in get_managed_rank_roles()]


def get_managed_role_ids() -> set[int]:
    """Return the set of managed Discord role IDs."""
    return {rank_role.discord_role_id for rank_role in get_managed_rank_roles()}


def get_all_role_names() -> list[str]:
    """Return all Discord role names in hierarchy order."""
    return [rank_role.discord_role_name for rank_role in RANK_ROLES]


def get_all_role_ids() -> set[int]:
    """Return the set of all configured Discord role IDs."""
    return {rank_role.discord_role_id for rank_role in RANK_ROLES}
