"""Configuration models for spec.yml parsing."""

from pathlib import Path
from typing import Literal
import yaml
from pydantic import BaseModel, Field


class HttpHealthCheck(BaseModel):
    """HTTP health check configuration."""
    type: Literal["http"] = "http"
    url: str
    expected_status: int = 200


class TcpHealthCheck(BaseModel):
    """TCP port health check configuration."""
    type: Literal["tcp"] = "tcp"
    host: str
    port: int


HealthCheck = HttpHealthCheck | TcpHealthCheck


class ArtifactConfig(BaseModel):
    """Artifact collection configuration."""
    collect: Literal["on_fail", "always"] = "on_fail"
    include_services: list[str] | None = None
    exclude_services: list[str] | None = None


class SpecConfig(BaseModel):
    """Main spec.yml configuration model."""
    compose_file: str
    base_url: str
    health_checks: list[dict] = Field(default_factory=list)
    suites: dict[str, str] = Field(default_factory=lambda: {
        "smoke": "smoke",
        "regression": "regression",
    })
    services: list[str] | None = None
    timeout: int = 120
    env_file: str | None = None
    artifacts: ArtifactConfig = Field(default_factory=ArtifactConfig)

    @classmethod
    def from_file(cls, path: str | Path) -> "SpecConfig":
        """Load configuration from a YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    def get_health_checks(self) -> list[HealthCheck]:
        """Parse health checks into typed models."""
        checks = []
        for check in self.health_checks:
            if check.get("type") == "tcp":
                checks.append(TcpHealthCheck(**check))
            else:
                checks.append(HttpHealthCheck(**check))
        return checks
