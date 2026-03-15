import os
from pathlib import Path

from dotenv import load_dotenv

from src.bot import GUILD_ID, TOKEN, client
from src.sync_planner import RolePolicy, SyncAction, plan_guild_sync_actions

load_dotenv()

ROLE_POLICY: RolePolicy = "exclusive"

OUTPUT_PATH = Path("scratch/test_sync_planner_output.txt")


def format_action(action: SyncAction) -> str:
    """Format one planned sync action for human-readable output."""
    return (
        f"{action.member_nickname} -> "
        f"{action.discord_user_id} -> "
        f"{action.action} {action.role_name}"
    )


@client.event
async def on_ready() -> None:
    print(f"Bot connected as {client.user}")

    guild = client.get_guild(GUILD_ID)
    if guild is None:
        raise RuntimeError(f"Guild {GUILD_ID} not found")

    members = [member async for member in guild.fetch_members(limit=None)]
    actions = plan_guild_sync_actions(members, ROLE_POLICY)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append(f"Guild: {guild.name} ({guild.id})")
    lines.append(f"Member count fetched: {len(members)}")
    lines.append(f"Planned action count: {len(actions)}")
    lines.append("")

    for action in actions:
        lines.append(format_action(action))

    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote planner output to: {OUTPUT_PATH}")

    await client.close()


if __name__ == "__main__":
    client.run(TOKEN)
