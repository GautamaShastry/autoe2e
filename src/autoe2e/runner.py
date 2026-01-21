"""Pytest test runner wrapper."""

import subprocess
import sys
from pathlib import Path


class TestRunner:
    """Wrapper for pytest execution."""

    def __init__(
        self,
        suite: str = "all",
        parallel: int | None = None,
        artifacts_dir: Path | None = None,
    ):
        self.suite = suite
        self.parallel = parallel
        self.artifacts_dir = artifacts_dir or Path("artifacts")

    def build_pytest_args(self, test_path: str = "tests") -> list[str]:
        """Build pytest command arguments."""
        args = [sys.executable, "-m", "pytest", test_path, "-v"]

        # Suite selection via markers
        if self.suite and self.suite != "all":
            args.extend(["-m", self.suite])

        # Parallel execution
        if self.parallel and self.parallel > 1:
            args.extend(["-n", str(self.parallel)])

        # JUnit XML output
        junit_path = self.artifacts_dir / "reports" / "junit.xml"
        junit_path.parent.mkdir(parents=True, exist_ok=True)
        args.extend(["--junit-xml", str(junit_path)])

        return args

    def run(self, test_path: str = "tests") -> int:
        """Execute pytest and return exit code."""
        args = self.build_pytest_args(test_path)
        result = subprocess.run(args)
        return result.returncode
