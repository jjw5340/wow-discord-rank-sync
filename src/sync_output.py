"""
Format sync planner and executor data for human-readable output.
"""

from __future__ import annotations

from src.sync_planner import SyncAction


def format_action(action: SyncAction) -> str:
    """Format one planned sync action for human-readable output."""
    preposition = "to" if action.action == "add" else "from"
    return (
        f"{action.action:<6} "
        f"{action.role_name:<8} "
        f"{preposition:<4} "
        f"{str(action.user_id):<19} "
        f"({action.user_name})"
    )
