"""
Run manual add/remove sync-action tests against TEST_USER_ID.

This runner:
- connects to Discord
- fetches the configured test user
- builds a small list of add/remove actions for managed roles
- prompts before every action
- applies actions through sync_executor.py
- writes results to scratch/test_run_sync_output.txt

Notes:
- The initial role state of the test user is assumed to be unknown.
- The final role state is not restored automatically.
- Some actions are intentionally duplicated to test skipped/no-op handling.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import discord
from dotenv import load_dotenv

from src.bot import DISCORD_BOT_TOKEN, DISCORD_GUILD_ID, client
from src.rank_roles import get_managed_rank_roles
from src.sync_planner import SyncAction
from src.sync_executor import SyncResult, apply_sync_action
from src.sync_output import format_action, format_result

load_dotenv()

test_user_id_raw = os.getenv("TEST_USER_ID")
if not test_user_id_raw:
    raise RuntimeError("TEST_USER_ID is not set")

try:
    TEST_USER_ID = int(test_user_id_raw)
except ValueError:
    raise RuntimeError("TEST_USER_ID must be an integer")

OUTPUT_PATH = Path("scratch/test_run_sync_output.txt")


def build_test_actions(member: discord.Member) -> list[SyncAction]:
    """Build a manual test sequence for one Discord member."""
    managed_rank_roles = get_managed_rank_roles()

    actions: list[SyncAction] = []

    for rank_role in managed_rank_roles:
        actions.append(
            SyncAction(
                user_id=member.id,
                user_name=member.display_name,
                role_id=rank_role.discord_role_id,
                role_name=rank_role.discord_role_name,
                action="add",
            )
        )

    if managed_rank_roles:
        first_rank_role = managed_rank_roles[0]
        actions.append(
            SyncAction(
                user_id=member.id,
                user_name=member.display_name,
                role_id=first_rank_role.discord_role_id,
                role_name=first_rank_role.discord_role_name,
                action="add",
            )
        )

    for rank_role in managed_rank_roles:
        actions.append(
            SyncAction(
                user_id=member.id,
                user_name=member.display_name,
                role_id=rank_role.discord_role_id,
                role_name=rank_role.discord_role_name,
                action="remove",
            )
        )

    if managed_rank_roles:
        first_rank_role = managed_rank_roles[0]
        actions.append(
            SyncAction(
                user_id=member.id,
                user_name=member.display_name,
                role_id=first_rank_role.discord_role_id,
                role_name=first_rank_role.discord_role_name,
                action="remove",
            )
        )

    return actions


async def prompt_to_continue(action: SyncAction) -> bool:
    """Prompt in the terminal before applying one action."""
    prompt = f"Apply action? {format_action(action)} [y/N/q]: "
    response = await asyncio.to_thread(input, prompt)
    normalized = response.strip().lower()

    if normalized == "q":
        raise KeyboardInterrupt("Execution aborted by user")

    return normalized == "y"


def build_output_lines(
    guild: discord.Guild,
    member: discord.Member,
    actions: list[SyncAction],
    results: list[SyncResult],
) -> list[str]:
    """Build output lines for the manual sync-action test run."""
    lines: list[str] = []
    lines.append("wow-discord-rank-sync")
    lines.append("Manual SyncAction executor test")
    lines.append("")
    lines.append(f"Discord Server: {guild.name} ({guild.id})")
    lines.append(f"Test User: {member.id} ({member.display_name})")
    lines.append(f"Planned action count: {len(actions)}")
    lines.append(f"Recorded result count: {len(results)}")
    lines.append("")
    lines.append("Planned Actions")
    lines.append("---------------")

    if actions:
        for action in actions:
            lines.append(format_action(action))
    else:
        lines.append("<none>")

    lines.append("")
    lines.append("Execution Results")
    lines.append("-----------------")

    if results:
        for result in results:
            lines.append(format_result(result))
    else:
        lines.append("<none>")

    return lines


@client.event
async def on_ready() -> None:
    print(f"Bot connected as {client.user}")

    guild = client.get_guild(DISCORD_GUILD_ID)
    if guild is None:
        raise RuntimeError(f"Guild {DISCORD_GUILD_ID} not found")

    member = guild.get_member(TEST_USER_ID)
    if member is None:
        member = await guild.fetch_member(TEST_USER_ID)

    actions = build_test_actions(member)
    results: list[SyncResult] = []

    print(f"Prepared {len(actions)} test actions for {member.display_name}")

    for action in actions:
        should_apply = await prompt_to_continue(action)
        if not should_apply:
            skipped_result = SyncResult(
                action=action,
                verdict="skipped",
                detail="skipped by operator",
            )
            results.append(skipped_result)
            print(format_result(skipped_result))
            continue

        result = await apply_sync_action(guild, action)
        results.append(result)
        print(format_result(result))

    output_lines = build_output_lines(guild, member, actions, results)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(output_lines) + "\n", encoding="utf-8")

    print(f"Wrote test output to: {OUTPUT_PATH}")

    await client.close()


if __name__ == "__main__":
    client.run(DISCORD_BOT_TOKEN)
