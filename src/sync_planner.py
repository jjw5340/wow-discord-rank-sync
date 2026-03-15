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
    get_managed_role_names,
    get_rank_role_by_guild_rank,
)

RolePolicy = Literal["exclusive", "nested"]
ActionType = Literal["add", "remove"]


@dataclass(frozen=True)
class SyncAction:
    member_nickname: str
    discord_user_id: int
    action: ActionType
    role_name: str


def desired_role_names_for_rank(rank_name: str, role_policy: RolePolicy) -> list[str]:
    """
    Return the desired Discord role names for a GRM rank.

    Exclusive policy:
        Raider -> ["Raiders"]

    Nested policy:
        Raider -> ["Raiders", "Trials", "Socials"]

    The order of RANK_ROLES is significant and is expected to be highest to lowest.
    """
    rank_role = get_rank_role_by_guild_rank(rank_name)
    if rank_role is None:
        raise ValueError(f"Unknown GRM rank: {rank_name!r}")

    if role_policy == "exclusive":
        return [rank_role.discord_role_name] if rank_role.managed_role else []

    if role_policy == "nested":
        start_index = RANK_ROLES.index(rank_role)
        return [
            item.discord_role_name
            for item in RANK_ROLES[start_index:]
            if item.managed_role
        ]

    raise ValueError(f"Unknown role_policy: {role_policy!r}")


def build_desired_role_names_by_discord_user_id(
    role_policy: RolePolicy,
) -> dict[int, list[str]]:
    """
    Build the desired Discord role names keyed by Discord user ID.

    Members with no Discord user ID are skipped.
    Members whose GRM rank does not map to a configured role are skipped.
    """
    mains: list[MainCharacter] = load_main_characters()
    desired: dict[int, list[str]] = {}

    for member in mains:
        if member.discord_user_id is None:
            continue

        if member.rank_name is None:
            continue

        try:
            desired_role_names = desired_role_names_for_rank(member.rank_name, role_policy)
        except ValueError:
            continue

        desired[member.discord_user_id] = desired_role_names

    return desired


def get_current_managed_role_names(member: discord.Member) -> set[str]:
    """Return the managed Discord role names currently assigned to a member."""
    managed_role_names = set(get_managed_role_names())
    return {role.name for role in member.roles if role.name in managed_role_names}


def plan_member_sync_actions(
    member: discord.Member,
    desired_role_names: list[str] | None,
) -> list[SyncAction]:
    """
    Plan add/remove actions for one Discord member.

    If desired_role_names is None, the member should have no managed roles.
    """
    current_role_names = get_current_managed_role_names(member)
    desired_role_names = desired_role_names or []
    desired_role_names_set = set(desired_role_names)

    actions: list[SyncAction] = []

    # Plan removals for managed roles the member should no longer have
    for role_name in sorted(current_role_names - desired_role_names_set):
        actions.append(
            SyncAction(
                member_nickname=member.display_name,
                discord_user_id=member.id,
                action="remove",
                role_name=role_name,
            )
        )

    # Plan additions in the configured hierarchy order
    for role_name in desired_role_names:
        if role_name not in current_role_names:
            actions.append(
                SyncAction(
                    member_nickname=member.display_name,
                    discord_user_id=member.id,
                    action="add",
                    role_name=role_name,
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
    desired_by_user_id = build_desired_role_names_by_discord_user_id(role_policy)

    actions: list[SyncAction] = []

    for member in members:
        desired_role_names = desired_by_user_id.get(member.id)
        actions.extend(plan_member_sync_actions(member, desired_role_names))

    return actions
