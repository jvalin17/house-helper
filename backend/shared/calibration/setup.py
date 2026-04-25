"""Offline model download and system requirements check.

Handles downloading Sentence Transformers and spaCy models
when user enables offline mode.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

REQUIRED_DISK_MB = 500
REQUIRED_RAM_MB = 2048


@dataclass
class SystemCheck:
    """Result of a system requirements check."""

    has_enough_disk: bool
    has_enough_ram: bool
    available_disk_mb: int
    available_ram_mb: int
    is_ready: bool


def check_system_requirements(data_dir: Path | None = None) -> SystemCheck:
    """Check if the system meets offline mode requirements."""
    disk_path = data_dir or Path.home()
    disk_usage = shutil.disk_usage(str(disk_path))
    available_disk_mb = disk_usage.free // (1024 * 1024)

    # RAM check: just report available, let user decide
    import os

    total_ram_mb = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") // (1024 * 1024)

    has_enough_disk = available_disk_mb >= REQUIRED_DISK_MB
    has_enough_ram = total_ram_mb >= REQUIRED_RAM_MB

    return SystemCheck(
        has_enough_disk=has_enough_disk,
        has_enough_ram=has_enough_ram,
        available_disk_mb=available_disk_mb,
        available_ram_mb=total_ram_mb,
        is_ready=has_enough_disk and has_enough_ram,
    )
