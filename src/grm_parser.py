"""
Extract data from GRM's SavedVariables file (Guild_Roster_Manager.lua).

Current understanding of tables saved in Guild_Roster_Manager.lua:
- GRM_GuildMemberHistory_Save: active/current guild member records
- GRM_Alts: main/alt relationship data
- GRM_PlayerListOfAlts_Save: personal alt list for the logged-in account (ignored)

Process:
- Build the set of all characters set as mains in GRM_Alts[guild], and extract:
    - character_name
- For each main, look up the corresponding active member record in
  GRM_GuildMemberHistory_Save[guild], and extract:
    - rank_name
    - discord_user_id (parsed from officerNote when it contains a plausible ID)

Output format:
[
    {
        "character_name": "...",
        "rank_name": "...",
        "discord_user_id": int | None
    },
    ...
]

Tested against GRM VERSION 1.99382 - February 28th, 2026
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any
from dataclasses import dataclass


@dataclass
class MainCharacter:
    character_name: str
    rank_name: str | None
    discord_user_id: int | None


DISCORD_USER_ID_PATTERN = re.compile(r"\b\d{17,20}\b")


def load_grm_file_text(path: str | os.PathLike[str]) -> str:
    """Read a full GRM SavedVariables Lua file."""
    return Path(path).read_text(encoding="utf-8")


def extract_table_block(text: str, table_name: str) -> str:
    """Extract a full top-level Lua table block like NAME = { ... }."""
    start_token = f"{table_name} = {{"
    start_index = text.find(start_token)
    if start_index == -1:
        raise ValueError(f"Could not find table {table_name!r}")

    brace_start = text.find("{", start_index)
    if brace_start == -1:
        raise ValueError(f"Could not find opening brace for table {table_name!r}")

    depth = 0
    for i in range(brace_start, len(text)):
        char = text[i]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start_index : i + 1]

    raise ValueError(f"Could not find closing brace for table {table_name!r}")


def extract_guild_block(table_block: str, guild_name: str) -> str:
    """Extract the specified guild block from a top-level GRM table."""
    guild_key = f'["{guild_name}"] = {{'
    guild_index = table_block.find(guild_key)
    if guild_index == -1:
        raise ValueError(f"Could not find guild {guild_name!r} in table block")

    brace_start = table_block.find("{", guild_index)
    if brace_start == -1:
        raise ValueError(f"Could not find opening brace for guild {guild_name!r}")

    depth = 0
    for i in range(brace_start, len(table_block)):
        char = table_block[i]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return table_block[guild_index : i + 1]

    raise ValueError(f"Could not find closing brace for guild {guild_name!r}")


def split_top_level_entries(block: str) -> list[str]:
    """
    Split a Lua table block into its immediate child entries.

    Input format:
        ["Something"] = {
            ["Child1"] = { ... },
            ["Child2"] = { ... },
        }
    """
    brace_start = block.find("{")
    if brace_start == -1:
        raise ValueError("Could not find opening brace in block")

    entries: list[str] = []
    depth = 0
    entry_start: int | None = None

    for i in range(brace_start + 1, len(block)):
        char = block[i]

        if depth == 0 and block.startswith('["', i):
            entry_start = i

        if char == "{":
            depth += 1
        elif char == "}":
            if depth == 0:
                if entry_start is not None:
                    entry = block[entry_start:i].rstrip(", \n\r\t")
                    if entry:
                        entries.append(entry)
                break
            depth -= 1
            if depth == 0 and entry_start is not None:
                j = i + 1
                while j < len(block) and block[j] in ", \n\r\t":
                    j += 1
                entry = block[entry_start:j].rstrip(", \n\r\t")
                if entry:
                    entries.append(entry)
                entry_start = None

    return entries


def parse_entry_key(entry: str) -> str:
    """Parse the key from an entry like ["Name-Realm"] = { ... }."""
    match = re.match(r'\["([^"]+)"\]\s*=\s*\{', entry.strip())
    if not match:
        raise ValueError("Could not parse entry key")
    return match.group(1)


def parse_string_field(entry: str, field_name: str) -> str | None:
    """Extract a string field from a member/group entry."""
    match = re.search(rf'\["{re.escape(field_name)}"\]\s*=\s*"([^"]*)"', entry)
    if not match:
        return None
    return match.group(1)


def parse_discord_user_id(officer_note: str | None) -> int | None:
    """Extract a plausible Discord user ID from officerNote."""
    if not officer_note:
        return None

    match = DISCORD_USER_ID_PATTERN.search(officer_note.strip())
    if not match:
        return None

    return int(match.group(0))


def parse_main_names(text: str, guild_name: str) -> list[str]:
    """
    Return all characters marked as mains in GRM_Alts[guild].

    Based on observed GRM structure, each alt-group entry contains:
        ["main"] = "Character-Realm"
    """
    table_block = extract_table_block(text, "GRM_Alts")
    guild_block = extract_guild_block(table_block, guild_name)
    alt_group_entries = split_top_level_entries(guild_block)

    main_names: list[str] = []
    for entry in alt_group_entries:
        main_name = parse_string_field(entry, "main")
        if main_name:
            main_names.append(main_name)

    return main_names


def parse_active_member_map(text: str, guild_name: str) -> dict[str, dict[str, Any]]:
    """
    Build a lookup of active member records from GRM_GuildMemberHistory_Save[guild].

    Keys are character names with server names like 'Odi-Dreamscythe'.
    """
    table_block = extract_table_block(text, "GRM_GuildMemberHistory_Save")
    guild_block = extract_guild_block(table_block, guild_name)
    member_entries = split_top_level_entries(guild_block)

    member_map: dict[str, dict[str, Any]] = {}
    for entry in member_entries:
        character_name = parse_entry_key(entry)
        rank_name = parse_string_field(entry, "rankName")
        officer_note = parse_string_field(entry, "officerNote")

        if rank_name is None:
            raise RuntimeError(
                f"GRM parser error: expected 'rankName' field for {character_name}"
            )

        if "officerNote" not in entry:
            raise RuntimeError(
                f"GRM parser error: expected 'officerNote' field for {character_name}"
            )

        member_map[character_name] = {
            "character_name": character_name,
            "rank_name": rank_name,
            "officer_note": officer_note,
        }

    return member_map


def build_main_character_rank_list(text: str, guild_name: str) -> list[MainCharacter]:
    """
    Return one record per main character with rank and Discord user ID.

    Output shape:
        [
            {
                "character_name": "...",
                "rank_name": "...",
                "discord_user_id": 123456789012345678 | None,
            },
            ...
        ]
    """
    main_names = parse_main_names(text, guild_name)
    member_map = parse_active_member_map(text, guild_name)

    results: list[dict[str, Any]] = []
    missing_from_member_history: list[str] = []

    for main_name in main_names:
        member = member_map.get(main_name)
        if member is None:
            missing_from_member_history.append(main_name)
            continue

        results.append(
            MainCharacter(
                character_name=main_name,
                rank_name=member["rank_name"],
                discord_user_id=parse_discord_user_id(member["officer_note"]),
            )
        )

    if missing_from_member_history:
        print("Warning: some mains were not found in GRM_GuildMemberHistory_Save:")
        for name in missing_from_member_history:
            print(f"  {name}")

    return results


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    grm_path = os.getenv("GRM_SAVEDVARIABLES_PATH")
    grm_guild_name = os.getenv("GRM_GUILD_NAME")

    if not grm_path:
        raise RuntimeError("GRM_SAVEDVARIABLES_PATH is not set")

    if not grm_guild_name:
        raise RuntimeError("GRM_GUILD_NAME is not set")

    text = load_grm_file_text(grm_path)
    mains = build_main_character_rank_list(text, grm_guild_name)

    print(f"Main count: {len(mains)}")
    print()

    for member in mains[:50]:
        print(member)
