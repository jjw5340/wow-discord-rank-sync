import os
from pathlib import Path

from dotenv import load_dotenv

from src.bot import DISCORD_GUILD_ID, DISCORD_BOT_TOKEN, client
from src.sync_planner import RolePolicy, SyncAction, plan_guild_sync_actions

load_dotenv()

ROLE_POLICY: RolePolicy = "exclusive"

OUTPUT_PATH = Path("scratch/test_sync_planner_output.txt")


def format_action(action: SyncAction) -> str:
    """Format one planned sync action for human-readable output."""
    preposition = "to" if action.action == "add" else "from"

    return (
        f"{action.action:<6} "
        f"{action.role_name:<8} "
        f"{preposition:<4} "
        f"{str(action.discord_user_id):<19} "
        f"({action.member_nickname})"
    )


@client.event
async def on_ready() -> None:
    print(f"Bot connected as {client.user}")

    guild = client.get_guild(DISCORD_GUILD_ID)
    if guild is None:
        raise RuntimeError(f"Guild {DISCORD_GUILD_ID} not found")

    members = [member async for member in guild.fetch_members(limit=None)]
    actions = plan_guild_sync_actions(members, ROLE_POLICY)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    lines.append(f"Guild: {guild.name} ({guild.id})")
    lines.append(f"Fetched member count: {len(members)}")
    lines.append(f"Planned action count: {len(actions)}")
    lines.append("")

    for action in actions:
        lines.append(format_action(action))

    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote planner output to: {OUTPUT_PATH}")

    await client.close()


if __name__ == "__main__":
    client.run(DISCORD_BOT_TOKEN)
