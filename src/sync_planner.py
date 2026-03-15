"""
Plan Discord role synchronization actions from GRM-derived guild data.

This module compares:
- desired managed Discord roles derived from GRM mains
- current managed Discord roles on members in the Discord server

It returns a list of SyncAction records describing what should be added
or removed, but does not execute those actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import discord

from src.grm_parser import MainCharacter, load_main_characters
from src.rank_roles import (
    RANK_ROLES,
    RankRole,
    get_rank_role_by_guild_rank,
    get_rank_role_by_discord_role_id,
)

RolePolicy = Literal["exclusive", "nested"]
ActionType = Literal["add", "remove"]


@dataclass(frozen=True)
class SyncAction:
    user_id: int
    user_name: str
    role_id: int
    role_name: str
    action: ActionType


def desired_rank_roles_for_rank(
    rank_name: str,
    role_policy: RolePolicy,
) -> list[RankRole]:
    """
    Return the desired managed RankRole objects for a GRM rank.

    Exclusive policy:
        Raider -> [Raiders]

    Nested policy:
        Raider -> [Raiders, Trials, Socials]

    The order of RANK_ROLES is significant and is expected to be highest to lowest.
    """
    rank_role = get_rank_role_by_guild_rank(rank_name)
    if rank_role is None:
        raise ValueError(f"Unknown GRM rank: {rank_name!r}")

    if role_policy == "exclusive":
        return [rank_role] if rank_role.managed_role else []

    if role_policy == "nested":
        start_index = RANK_ROLES.index(rank_role)
        return [item for item in RANK_ROLES[start_index:] if item.managed_role]

    raise ValueError(f"Unknown role_policy: {role_policy!r}")


def build_desired_rank_roles_by_discord_user_id(
    role_policy: RolePolicy,
) -> dict[int, list[RankRole]]:
    """
    Build the desired managed RankRole objects keyed by Discord user ID.

    Members with no Discord user ID are skipped.
    Members whose GRM rank does not map to a configured role are skipped.
    """
    mains: list[MainCharacter] = load_main_characters()
    desired: dict[int, list[RankRole]] = {}

    for member in mains:
        if member.discord_user_id is None:
            continue

        if member.rank_name is None:
            continue

        try:
            desired_rank_roles = desired_rank_roles_for_rank(
                member.rank_name,
                role_policy,
            )
        except ValueError:
            continue

        desired[member.discord_user_id] = desired_rank_roles

    return desired


def get_current_managed_rank_roles(member: discord.Member) -> set[RankRole]:
    """Return the managed RankRole objects currently assigned to a member."""
    current_rank_role_set: set[RankRole] = set()

    for role in member.roles:
        rank_role = get_rank_role_by_discord_role_id(role.id)
        if rank_role is not None and rank_role.managed_role:
            current_rank_role_set.add(rank_role)

    return current_rank_role_set


def plan_member_sync_actions(
    member: discord.Member,
    desired_rank_roles: list[RankRole] | None,
) -> list[SyncAction]:
    """
    Plan add/remove actions for one Discord member.

    If desired_rank_roles is None, the member should have no managed roles.
    """
    desired_rank_roles = desired_rank_roles or []
    desired_rank_role_set = set(desired_rank_roles)
    current_rank_role_set = get_current_managed_rank_roles(member)

    actions: list[SyncAction] = []

    # Plan removals for managed roles the member should no longer have
    for rank_role in sorted(
        current_rank_role_set - desired_rank_role_set,
        key=lambda item: RANK_ROLES.index(item),
    ):
        actions.append(
            SyncAction(
                user_id=member.id,
                user_name=member.display_name,
                role_id=rank_role.discord_role_id,
                role_name=rank_role.discord_role_name,
                action="remove",
            )
        )

    # Plan additions in the configured hierarchy order
    for rank_role in desired_rank_roles:
        if rank_role not in current_rank_role_set:
            actions.append(
                SyncAction(
                    user_id=member.id,
                    user_name=member.display_name,
                    role_id=rank_role.discord_role_id,
                    role_name=rank_role.discord_role_name,
                    action="add",
                )
            )

    return actions


def plan_guild_sync_actions(
    members: list[discord.Member],
    role_policy: RolePolicy,
) -> list[SyncAction]:
    """
    Plan all managed-role sync actions for the provided Discord members.

    Members present in GRM desired state are aligned to their desired roles.
    Members absent from GRM desired state have all managed roles removed.
    """
    desired_by_user_id = build_desired_rank_roles_by_discord_user_id(role_policy)

    actions: list[SyncAction] = []

    for member in members:
        desired_rank_roles = desired_by_user_id.get(member.id)
        actions.extend(plan_member_sync_actions(member, desired_rank_roles))

    return actions
