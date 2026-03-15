"""
Execute Discord role changes planned by sync_planner.py.
"""

from __future__ import annotations

from dataclasses import dataclass

import discord

from src.sync_planner import ActionType, SyncAction


@dataclass(frozen=True)
class ExecutionResult:
    action: SyncAction
    status: str
    detail: str | None = None


async def get_member_or_fetch(
    guild: discord.Guild,
    discord_user_id: int,
) -> discord.Member | None:
    """Return a guild member by user ID, using cache first and fetch as fallback."""
    member = guild.get_member(discord_user_id)
    if member is not None:
        return member

    try:
        return await guild.fetch_member(discord_user_id)
    except discord.NotFound:
        return None


def get_role_by_name(guild: discord.Guild, role_name: str) -> discord.Role | None:
    """Return a guild role by its name."""
    return discord.utils.get(guild.roles, name=role_name)


async def apply_sync_action(
    guild: discord.Guild,
    action: SyncAction,
) -> ExecutionResult:
    """Apply one planned sync action to Discord."""
    member = await get_member_or_fetch(guild, action.user_id)
    if member is None:
        return ExecutionResult(
            action=action,
            status="skipped",
            detail="member not found",
        )

    role = get_role_by_name(guild, action.role_name)
    if role is None:
        return ExecutionResult(
            action=action,
            status="skipped",
            detail="role not found",
        )

    if action.action == "add":
        if role in member.roles:
            return ExecutionResult(
                action=action,
                status="noop",
                detail="member already has role",
            )

        await member.add_roles(role, reason="Guild rank sync")
        return ExecutionResult(
            action=action,
            status="applied",
        )

    if action.action == "remove":
        if role not in member.roles:
            return ExecutionResult(
                action=action,
                status="noop",
                detail="member does not have role",
            )

        await member.remove_roles(role, reason="Guild rank sync")
        return ExecutionResult(
            action=action,
            status="applied",
        )

    return ExecutionResult(
        action=action,
        status="skipped",
        detail=f"unknown action type: {action.action!r}",
    )


async def apply_sync_actions(
    guild: discord.Guild,
    actions: list[SyncAction],
) -> list[ExecutionResult]:
    """Apply a list of planned sync actions in order."""
    results: list[ExecutionResult] = []

    for action in actions:
        result = await apply_sync_action(guild, action)
        results.append(result)

    return results
