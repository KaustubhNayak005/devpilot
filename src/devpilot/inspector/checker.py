"""Tool availability checker for project inspection."""

from __future__ import annotations

from devpilot.utils.shell import which


def check_tools(tools: list[str]) -> dict[str, bool]:
    """Check which tools are available on the system PATH.

    Args:
        tools: List of tool/executable names to check.

    Returns:
        Dictionary mapping each tool name to True if found, False if not.
    """
    result: dict[str, bool] = {}
    for tool in tools:
        result[tool] = which(tool) is not None
    return result
