"""Docker Compose orchestration without Ansible."""

import json
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

import requests


class DockerRunner:
    """Manages Docker Compose environments directly."""

    def __init__(self, compose_file: str, run_id: str):
        self.compose_file = compose_file
        self.run_id = run_id
        self.project_name = f"autoe2e-{run_id}"

    def _run_compose(self, *args: str, capture: bool = False) -> subprocess.CompletedProcess:
        """Run a docker compose command."""
        cmd = [
            "docker", "compose",
            "-f", self.compose_file,
            "-p", self.project_name,
            *args
        ]
        if capture:
            return subprocess.run(cmd, capture_output=True, text=True)
        return subprocess.run(cmd)

    def up(self) -> int:
        """Start the Docker Compose stack."""
        result = self._run_compose("up", "-d", "--build", "--wait")
        return result.returncode

    def down(self, remove_volumes: bool = True) -> int:
        """Stop and remove the stack."""
        args = ["down", "--remove-orphans"]
        if remove_volumes:
            args.append("--volumes")
        result = self._run_compose(*args)
        return result.returncode

    def ps(self) -> str:
        """Get container status."""
        result = self._run_compose("ps", "-a", capture=True)
        return result.stdout

    def logs(self, service: str | None = None) -> str:
        """Get container logs."""
        args = ["logs", "--no-color"]
        if service:
            args.append(service)
        result = self._run_compose(*args, capture=True)
        return result.stdout + result.stderr

    def wait_for_health(
        self,
        health_checks: list[dict],
        timeout: int = 120,
        interval: int = 5,
    ) -> bool:
        """Wait for all health checks to pass."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            all_passed = True

            for check in health_checks:
                if check.get("type") == "http":
                    if not self._check_http(check):
                        all_passed = False
                        break
                elif check.get("type") == "tcp":
                    if not self._check_tcp(check):
                        all_passed = False
                        break

            if all_passed:
                return True

            time.sleep(interval)

        return False

    def _check_http(self, check: dict) -> bool:
        """Perform HTTP health check."""
        try:
            response = requests.get(check["url"], timeout=5)
            expected = check.get("expected_status", 200)
            return response.status_code == expected
        except Exception:
            return False

    def _check_tcp(self, check: dict) -> bool:
        """Perform TCP port check."""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((check["host"], check["port"]))
            sock.close()
            return result == 0
        except Exception:
            return False

    def collect_artifacts(self, artifacts_dir: Path, services: list[str] | None = None) -> None:
        """Collect logs and metadata."""
        # Create directories
        (artifacts_dir / "logs").mkdir(parents=True, exist_ok=True)
        (artifacts_dir / "reports").mkdir(parents=True, exist_ok=True)
        (artifacts_dir / "env").mkdir(parents=True, exist_ok=True)
        (artifacts_dir / "compose").mkdir(parents=True, exist_ok=True)

        # Collect logs
        logs = self.logs()
        (artifacts_dir / "logs" / "all.log").write_text(logs)

        # Copy compose file
        shutil.copy(self.compose_file, artifacts_dir / "compose" / "docker-compose.yml")

        # Container states
        ps_output = self.ps()
        (artifacts_dir / "env" / "container_states.txt").write_text(ps_output)

        # Docker versions
        docker_version = subprocess.run(
            ["docker", "version", "--format", "json"],
            capture_output=True, text=True
        )
        compose_version = subprocess.run(
            ["docker", "compose", "version", "--short"],
            capture_output=True, text=True
        )

        metadata = {
            "run_id": self.run_id,
            "collected_at": datetime.now().isoformat(),
            "compose_version": compose_version.stdout.strip(),
        }
        try:
            metadata["docker_version"] = json.loads(docker_version.stdout)
        except:
            metadata["docker_version"] = docker_version.stdout.strip()

        (artifacts_dir / "env" / "metadata.json").write_text(
            json.dumps(metadata, indent=2)
        )
