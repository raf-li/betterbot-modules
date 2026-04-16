# Copyright (c) 2026 Rafli.
# Author: Rafli (Fli)
# Copyright: © 2026 Rafli.
# Project Philosophy: "A high-end, decoupled, skeleton framework for TeamTalk 5."

"""
modules/example_module/utils.py — Helper utilities for the Example Module.

This file demonstrates the "separation of concerns" pattern.
Supporting logic that does not belong in the main class is extracted here,
keeping ``__init__.py`` clean and easy to read.
"""

from __future__ import annotations

import platform
import sys
from datetime import datetime
from typing import Any, Dict


def get_uptime_string(start_time: datetime) -> str:
    """
    Format a human-readable uptime string from a start timestamp.

    Args:
        start_time (datetime): The time at which the bot (or module) started.

    Returns:
        str: Uptime formatted as ``"Xh Xm Xs"`` (hours, minutes, seconds).

    Example:
        >>> from datetime import datetime
        >>> start = datetime(2026, 1, 1, 12, 0, 0)
        >>> get_uptime_string(start)
        '2h 30m 15s'
    """
    delta = datetime.now() - start_time
    total_seconds = int(delta.total_seconds())
    hours   = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours}h {minutes}m {seconds}s"


def get_system_info() -> Dict[str, str]:
    """
    Collect runtime system information for the ``.info`` command.

    Returns:
        Dict[str, str]: A dictionary containing:

            - ``python_version`` : Active Python version string
            - ``os``             : Operating system name
            - ``platform``       : Terse platform descriptor
    """
    return {
        "python_version": sys.version.split(" ")[0],
        "os"            : platform.system(),
        "platform"      : platform.platform(terse=True),
    }


def format_user_info(user_id: int, username: str, nickname: str) -> str:
    """
    Format user information into a readable string.

    Args:
        user_id  (int): TeamTalk User ID.
        username (str): Server account username.
        nickname (str): Display nickname.

    Returns:
        str: Formatted string, e.g. ``"Rafli (ID: 42, account: fli)"``
    """
    return f"{nickname} (ID: {user_id}, account: {username})"


def count_visitors(shared_data: Dict[str, Any], key: str = "example.visitor_count") -> int:
    """
    Increment and return the visitor counter stored in ``shared_data``.

    Demonstrates how to use ``shared_data`` for persistent state that other
    modules can read.

    Args:
        shared_data (Dict[str, Any]): The bot's shared state dictionary.
        key         (str):            Storage key inside ``shared_data``.
                                      Default: ``"example.visitor_count"``.

    Returns:
        int: The updated total visitor count.
    """
    count = shared_data.get(key, 0) + 1
    shared_data[key] = count
    return count
