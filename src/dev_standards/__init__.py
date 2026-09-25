"""Shared conventions, pre-commit hooks, and CI for the Discord bot and API repositories."""

from .config import Settings, load_settings
from .prose import Violation, check_file, check_paths
from .sync import sync
from .template import check_template

__all__ = [
    "Settings",
    "Violation",
    "check_file",
    "check_paths",
    "check_template",
    "load_settings",
    "sync",
]
