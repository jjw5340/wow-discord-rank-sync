"""
Run the full guild-rank synchronization workflow.

This entry point:
- connects to Discord
- fetches guild members
- plans sync actions
- logs a preview
- optionally applies actions either step-by-step or continuously
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Literal

import discord
from dotenv import load_dotenv

from src.bot import DISCORD_BOT_TOKEN, DISCORD_GUILD_ID, client
from src.sync_executor import SyncResult, apply_sync_action
from src.sync_planner import RolePolicy, SyncAction, plan_guild_sync_actions

load_dotenv()

RunMode = Literal["preview", "step_through", "continuous"]

RUN_MODE: RunMode = "preview"
ROLE_POLICY: RolePolicy = "exclusive"

log_channel_id_raw = os.getenv("DISCORD_LOG_CHANNEL_ID")
DISCORD_LOG_CHANNEL_ID = int(log_channel_id_raw) if log_channel_id_raw else None

OUTPUT_PATH = Path("scratch/run_sync_output.txt")


def format_action(action: SyncAction) -> str:
    """Format one planned sync action for human-readable output."""
    preposition = "to" if action.action == "add" else "from"
    return (
        f"{action.action} {action.role_name} {preposition} "
        f"{action.user_id} ({action.user_name})"
    )


def format_result(result: SyncResult) -> str:
    """Format one execution result for human-readable output."""
    action_text = format_action(result.action)
    if result.detail:
        return f"{result.verdict}: {action_text} [{result.detail}]"
    return f"{result.verdict}: {action_text}"


def build_preview_lines(
    guild: discord.Guild,
    members: list[discord.Member],
    actions: list[SyncAction],
) -> list[str]:
    """Build the preview section for planned sync actions."""
    lines: list[str] = []
    lines.append(f"Guild: {guild.name} ({guild.id})")
    lines.append(f"Fetched member count: {len(members)}")
    lines.append(f"Role policy: {ROLE_POLICY}")
    lines.append(f"Run mode: {RUN_MODE}")
    lines.append(f"Planned action count: {len(actions)}")
    lines.append("")
    lines.append("Planned Actions")
    lines.append("---------------")

    if actions:
        for action in actions:
            lines.append(format_action(action))
    else:
        lines.append("<none>")

    return lines


def build_result_lines(results: list[SyncResult]) -> list[str]:
    """Build the result section for executed sync actions."""
    lines: list[str] = []
    lines.append("")
    lines.append("Execution Results")
    lines.append("-----------------")

    if results:
        for result in results:
            lines.append(format_result(result))
    else:
        lines.append("<none>")

    return lines


async def send_log_message(channel: discord.abc.Messageable, lines: list[str]) -> None:
    """Send log lines to a Discord channel in chunks."""
    if not lines:
        return

    text = "\n".join(lines)
    max_chunk_size = 1800

    for start in range(0, len(text), max_chunk_size):
        chunk = text[start:start + max_chunk_size]
        await channel.send(f"```text\n{chunk}\n```")


async def prompt_to_continue(action: SyncAction) -> bool:
    """Prompt in the terminal before applying one action."""
    prompt = f"Apply action? {format_action(action)} [y/N/q]: "
    response = await asyncio.to_thread(input, prompt)
    normalized = response.strip().lower()

    if normalized == "q":
        raise KeyboardInterrupt("Execution aborted by user")

    return normalized == "y"


async def get_log_channel(guild: discord.Guild) -> discord.TextChannel | None:
    """Return the configured hidden log channel if available."""
    if DISCORD_LOG_CHANNEL_ID is None:
        return None

    channel = guild.get_channel(DISCORD_LOG_CHANNEL_ID)
    if channel is None:
        try:
            fetched = await client.fetch_channel(DISCORD_LOG_CHANNEL_ID)
        except discord.NotFound:
            return None
        if isinstance(fetched, discord.TextChannel):
            return fetched
        return None

    if isinstance(channel, discord.TextChannel):
        return channel

    return None


@client.event
async def on_ready() -> None:
    print(f"Bot connected as {client.user}")

    guild = client.get_guild(DISCORD_GUILD_ID)
    if guild is None:
        raise RuntimeError(f"Guild {DISCORD_GUILD_ID} not found")

    members = [member async for member in guild.fetch_members(limit=None)]
    actions = plan_guild_sync_actions(members, ROLE_POLICY)

    preview_lines = build_preview_lines(guild, members, actions)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(preview_lines) + "\n", encoding="utf-8")

    print(f"Wrote preview output to: {OUTPUT_PATH}")

    log_channel = await get_log_channel(guild)
    if log_channel is not None:
        await send_log_message(log_channel, preview_lines)

    if RUN_MODE == "preview":
        print("Preview complete; no role changes were applied.")
        await client.close()
        return

    results: list[SyncResult] = []

    for action in actions:
        if RUN_MODE == "step_through":
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

    result_lines = build_result_lines(results)

    with OUTPUT_PATH.open("a", encoding="utf-8") as f:
        f.write("\n".join(result_lines) + "\n")

    if log_channel is not None:
        await send_log_message(log_channel, result_lines)

    print(f"Execution complete; appended results to: {OUTPUT_PATH}")

    await client.close()


if __name__ == "__main__":
    client.run(DISCORD_BOT_TOKEN)
