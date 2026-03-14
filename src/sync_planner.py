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

from src.bot import RANK_NAME_TO_ROLE_NAME, ROLE_NAME_TO_ROLE_ID
from src.grm_parser import MainCharacter, load_main_characters

RolePolicy = Literal["exclusive", "nested"]
ActionType = Literal["add", "remove"]

ROLE_POLICY: RolePolicy = "exclusive"


@dataclass(frozen=True)
class SyncAction:
    member_display_name: str
    discord_user_id: int
    action: ActionType
    role_name: str


def get_managed_role_names() -> set[str]:
    """Return the set of Discord role names managed by this project."""
    return set(ROLE_NAME_TO_ROLE_ID.keys())


def desired_role_names_for_rank(rank_name: str) -> list[str]:
    """
    Return the desired managed Discord role names for a GRM rank.

    Exclusive policy:
        Raider -> {"Raiders"}

    Nested policy:
        Raider -> {"Raiders", "Trials", "Socials"}
    """
    primary_role_name = RANK_NAME_TO_ROLE_NAME.get(rank_name)
    if primary_role_name is None:
        raise ValueError(f"Unknown GRM rank: {rank_name!r}")

    if ROLE_POLICY == "exclusive":
        return {primary_role_name}

    if ROLE_POLICY == "nested":
        ordered_roles = ["Socials", "Trials", "Raiders", "Veterans"]
        if primary_role_name not in ordered_roles:
            raise ValueError(
                f"Primary role {primary_role_name!r} is not in nested role ordering"
            )

        max_index = ordered_roles.index(primary_role_name)

        return set(ordered_roles[: max_index + 1])

    raise ValueError(f"Unknown ROLE_POLICY: {ROLE_POLICY!r}")


def build_desired_role_names_by_discord_user_id() -> dict[int, set[str]]:
    """
    Build the desired managed Discord role names keyed by Discord user ID.

    Members with no Discord user ID are skipped.
    Members whose GRM rank does not map to a configured role are skipped.
    """
    mains: list[MainCharacter] = load_main_characters()

    desired: dict[int, set[str]] = {}

    for member in mains:
        if member.discord_user_id is None:
            continue

        if member.rank_name is None:
            continue

        try:
            desired_role_names = desired_role_names_for_rank(member.rank_name)
        except ValueError:
            continue

        desired[member.discord_user_id] = desired_role_names

    return desired


def get_current_managed_role_names(member: discord.Member) -> set[str]:
    """Return the currently assigned managed role names for a Discord member."""
    managed_role_names = get_managed_role_names()
    return {role.name for role in member.roles if role.name in managed_role_names}


def plan_member_sync_actions(
    member: discord.Member,
    desired_role_names: set[str] | None,
) -> list[SyncAction]:
    """
    Plan add/remove actions for a single Discord member.

    If desired_role_names is None, the member should have no managed roles.
    """
    current_role_names = get_current_managed_role_names(member)
    desired_role_names = desired_role_names or set()

    actions: list[SyncAction] = []

    for role_name in sorted(current_role_names - desired_role_names):
        actions.append(
            SyncAction(
                member_display_name=member.display_name,
                discord_user_id=member.id,
                action="remove",
                role_name=role_name,
            )
        )

    for role_name in sorted(desired_role_names - current_role_names):
        actions.append(
            SyncAction(
                member_display_name=member.display_name,
                discord_user_id=member.id,
                action="add",
                role_name=role_name,
            )
        )

    return actions


def plan_guild_sync_actions(members: list[discord.Member]) -> list[SyncAction]:
    """
    Plan all managed-role sync actions for the provided Discord members.

    Members present in GRM desired state are aligned to their desired managed roles.
    Members absent from GRM desired state have all managed roles removed.
    """
    desired_by_user_id = build_desired_role_names_by_discord_user_id()

    actions: list[SyncAction] = []

    for member in members:
        desired_role_names = desired_by_user_id.get(member.id)
        actions.extend(plan_member_sync_actions(member, desired_role_names))

    return actions
