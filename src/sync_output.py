"""
Format sync planner and executor data for human-readable output.
"""

from __future__ import annotations

from src.sync_planner import SyncAction
from src.sync_executor import SyncResult


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


def format_result(result: SyncResult) -> str:
    """Format one execution result for human-readable output."""
    action_text = format_action(result.action)
    if result.detail:
        return f"{result.verdict}: {action_text} [{result.detail}]"
    return f"{result.verdict}: {action_text}"
