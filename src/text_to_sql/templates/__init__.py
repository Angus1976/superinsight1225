"""
SQL Templates for Text-to-SQL generation.

This package contains predefined SQL templates for common query patterns.
"""

import os
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent

def get_templates_path() -> str:
    """Get the path to the templates directory."""
    return str(TEMPLATES_DIR)

def get_default_templates_file() -> str:
    """Get the path to the default templates file."""
    return str(TEMPLATES_DIR / "default_templates.json")
