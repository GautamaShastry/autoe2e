"""Ansible playbook execution wrapper."""

import json
import os
import subprocess
from pathlib import Path
from typing import Any


class AnsibleRunner:
    """Executes Ansible playbooks for environment management."""

    def __init__(self, playbooks_dir: Path | None = None):
        self.playbooks_dir = playbooks_dir or self._find_playbooks_dir()
        self.working_dir = Path.cwd()

    def _find_playbooks_dir(self) -> Path:
        """Locate the playbooks directory."""
        # Check relative to package
        pkg_dir = Path(__file__).parent
        candidates = [
            pkg_dir / "playbooks",
            pkg_dir.parent.parent / "playbooks",
            Path.cwd() / "playbooks",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return Path.cwd() / "playbooks"

    def _resolve_path(self, path: str) -> str:
        """Convert relative path to absolute path."""
        p = Path(path)
        if not p.is_absolute():
            p = self.working_dir / p
        return str(p.resolve())

    def run_playbook(
        self,
        playbook: str,
        extra_vars: dict[str, Any] | None = None,
        verbose: bool = False,
    ) -> int:
        """Run an Ansible playbook and return exit code."""
        playbook_path = self.playbooks_dir / playbook

        cmd = [
            "ansible-playbook",
            str(playbook_path),
            "-i", "localhost,",
            "-c", "local",
        ]

        if extra_vars:
            cmd.extend(["-e", json.dumps(extra_vars)])

        if verbose:
            cmd.append("-v")

        env = os.environ.copy()
        env["ANSIBLE_LOCALHOST_WARNING"] = "False"
        env["ANSIBLE_INVENTORY_UNPARSED_WARNING"] = "False"

        result = subprocess.run(cmd, env=env)
        return result.returncode

    def up(
        self,
        compose_file: str,
        run_id: str,
        health_checks: list[dict],
        timeout_secs: int = 120,
        env_file: str | None = None,
    ) -> int:
        """Bring up the Docker Compose environment."""
        extra_vars = {
            "compose_file": self._resolve_path(compose_file),
            "run_id": run_id,
            "health_checks": health_checks,
            "timeout_secs": timeout_secs,
        }
        if env_file:
            extra_vars["env_file"] = self._resolve_path(env_file)

        return self.run_playbook("up.yml", extra_vars)

    def down(
        self,
        compose_file: str,
        run_id: str,
        remove_volumes: bool = True,
    ) -> int:
        """Tear down the Docker Compose environment."""
        extra_vars = {
            "compose_file": self._resolve_path(compose_file),
            "run_id": run_id,
            "remove_volumes": remove_volumes,
        }
        return self.run_playbook("down.yml", extra_vars)

    def collect_artifacts(
        self,
        compose_file: str,
        run_id: str,
        artifacts_dir: str,
        services: list[str] | None = None,
    ) -> int:
        """Collect logs and artifacts from the environment."""
        extra_vars = {
            "compose_file": self._resolve_path(compose_file),
            "run_id": run_id,
            "artifacts_dir": self._resolve_path(artifacts_dir),
        }
        if services:
            extra_vars["services"] = services

        return self.run_playbook("collect_artifacts.yml", extra_vars)

    def status(self, compose_file: str) -> int:
        """Show status of containers."""
        extra_vars = {"compose_file": self._resolve_path(compose_file)}
        return self.run_playbook("status.yml", extra_vars)
