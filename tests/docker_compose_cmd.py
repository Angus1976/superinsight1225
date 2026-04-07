"""
Resolve the docker compose CLI as a argv prefix: ``docker-compose`` or ``docker compose``.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import List, Optional


def docker_compose_argv_prefix() -> Optional[List[str]]:
    """Return ``['docker-compose']`` or ``['docker', 'compose']``, or None if unavailable."""
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return None
    try:
        subprocess.run(
            [docker_bin, "compose", "version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return None
    return ["docker", "compose"]
