"""Report generation for test runs."""

import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any


class Reporter:
    """Generates summary.json from test results."""

    def __init__(self, run_id: str, artifacts_dir: Path):
        self.run_id = run_id
        self.artifacts_dir = artifacts_dir
        self.start_time: datetime | None = None
        self.env_ready_time: datetime | None = None
        self.test_end_time: datetime | None = None

    def mark_start(self) -> None:
        """Mark the start of the run."""
        self.start_time = datetime.now()

    def mark_env_ready(self) -> None:
        """Mark when environment is ready."""
        self.env_ready_time = datetime.now()

    def mark_test_end(self) -> None:
        """Mark when tests complete."""
        self.test_end_time = datetime.now()

    def parse_junit_xml(self) -> dict[str, Any]:
        """Parse JUnit XML for test results."""
        junit_path = self.artifacts_dir / "reports" / "junit.xml"
        if not junit_path.exists():
            return {"total": 0, "passed": 0, "failed": 0, "failures": []}

        tree = ET.parse(junit_path)
        root = tree.getroot()

        testsuite = root.find("testsuite") or root
        total = int(testsuite.get("tests", 0))
        failures_count = int(testsuite.get("failures", 0))
        errors_count = int(testsuite.get("errors", 0))

        failures = []
        for testcase in testsuite.findall("testcase"):
            failure = testcase.find("failure")
            error = testcase.find("error")
            if failure is not None or error is not None:
                elem = failure if failure is not None else error
                failures.append({
                    "name": f"{testcase.get('classname')}.{testcase.get('name')}",
                    "reason": (elem.get("message", "")[:200] if elem is not None else ""),
                })

        return {
            "total": total,
            "passed": total - failures_count - errors_count,
            "failed": failures_count + errors_count,
            "failures": failures,
        }

    def generate_summary(self, exit_code: int) -> dict[str, Any]:
        """Generate the summary.json content."""
        test_results = self.parse_junit_xml()

        env_time = None
        if self.start_time and self.env_ready_time:
            env_time = (self.env_ready_time - self.start_time).total_seconds()

        test_time = None
        if self.env_ready_time and self.test_end_time:
            test_time = (self.test_end_time - self.env_ready_time).total_seconds()

        return {
            "run_id": self.run_id,
            "timestamp": self.start_time.isoformat() if self.start_time else None,
            "exit_code": exit_code,
            "environment_bring_up_time_seconds": env_time,
            "test_runtime_seconds": test_time,
            "total_tests": test_results["total"],
            "passed": test_results["passed"],
            "failed": test_results["failed"],
            "failures": test_results["failures"],
        }

    def write_summary(self, exit_code: int) -> Path:
        """Write summary.json to artifacts directory."""
        summary = self.generate_summary(exit_code)
        reports_dir = self.artifacts_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        summary_path = reports_dir / "summary.json"
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

        return summary_path
