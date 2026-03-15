"""
Execute Discord role changes planned by sync_planner.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import discord

from src.sync_planner import SyncAction


SyncVerdict = Literal["applied", "skipped"]


@dataclass(frozen=True)
class SyncResult:
    action: SyncAction
    verdict: SyncVerdict
    detail: str | None = None


async def get_member(
    guild: discord.Guild,
    user_id: int,
) -> discord.Member | None:
    """Return a guild member by user ID, using cache first and fetch as fallback."""
    member = guild.get_member(user_id)
    if member is not None:
        return member

    try:
        return await guild.fetch_member(user_id)
    except discord.NotFound:
        return None


def get_role(
    guild: discord.Guild,
    role_id: int,
) -> discord.Role | None:
    """Return a guild role by its Discord role ID."""
    return guild.get_role(role_id)


async def apply_sync_action(
    guild: discord.Guild,
    action: SyncAction,
) -> SyncResult:
    """Apply one planned sync action to Discord."""
    member = await get_member(guild, action.user_id)
    if member is None:
        return SyncResult(
            action=action,
            verdict="skipped",
            detail="member not found",
        )

    role = get_role(guild, action.role_id)
    if role is None:
        return SyncResult(
            action=action,
            verdict="skipped",
            detail="role not found",
        )

    if action.action == "add":
        if role in member.roles:
            return SyncResult(
                action=action,
                verdict="skipped",
                detail="member already has role",
            )

        await member.add_roles(role, reason="Guild rank sync")
        return SyncResult(
            action=action,
            verdict="applied",
        )

    if action.action == "remove":
        if role not in member.roles:
            return SyncResult(
                action=action,
                verdict="skipped",
                detail="member does not have role",
            )

        await member.remove_roles(role, reason="Guild rank sync")
        return SyncResult(
            action=action,
            verdict="applied",
        )

    return SyncResult(
        action=action,
        verdict="skipped",
        detail=f"unknown action type: {action.action!r}",
    )


async def apply_sync_actions(
    guild: discord.Guild,
    actions: list[SyncAction],
) -> list[SyncResult]:
    """Apply a list of planned sync actions in order."""
    results: list[SyncResult] = []

    for action in actions:
        result = await apply_sync_action(guild, action)
        results.append(result)

    return results
