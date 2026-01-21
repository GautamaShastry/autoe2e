"""CLI commands for AutoE2E."""

import sys
import uuid
from pathlib import Path

import click

from .ansible_runner import AnsibleRunner
from .config import SpecConfig
from .reporter import Reporter
from .runner import TestRunner


def generate_run_id() -> str:
    """Generate a unique run ID."""
    return uuid.uuid4().hex[:12]


@click.group()
@click.version_option()
def main():
    """AutoE2E - One-command E2E testing with containerized environments."""
    pass


@main.command()
@click.option("-f", "--file", "spec_file", required=True, help="Path to spec.yml")
@click.option("--timeout", type=int, help="Readiness timeout in seconds")
def up(spec_file: str, timeout: int | None):
    """Start Docker Compose stack and wait for readiness."""
    config = SpecConfig.from_file(spec_file)
    run_id = generate_run_id()

    click.echo(f"Starting environment (run_id: {run_id})...")

    ansible = AnsibleRunner()
    health_checks = [c.model_dump() for c in config.get_health_checks()]

    exit_code = ansible.up(
        compose_file=config.compose_file,
        run_id=run_id,
        health_checks=health_checks,
        timeout_secs=timeout or config.timeout,
        env_file=config.env_file,
    )

    if exit_code == 0:
        click.echo(click.style("Environment is ready!", fg="green"))
    else:
        click.echo(click.style("Failed to start environment", fg="red"))

    sys.exit(exit_code)


@main.command()
@click.option("-f", "--file", "spec_file", required=True, help="Path to spec.yml")
@click.option("--suite", default="all", help="Test suite: smoke, regression, or all")
@click.option("--parallel", "-n", type=int, help="Number of parallel workers")
@click.option("--artifacts-dir", type=click.Path(), help="Artifacts directory")
def test(spec_file: str, suite: str, parallel: int | None, artifacts_dir: str | None):
    """Run E2E tests via pytest."""
    SpecConfig.from_file(spec_file)  # Validate config
    run_id = generate_run_id()

    artifacts_path = Path(artifacts_dir) if artifacts_dir else Path("artifacts") / run_id
    artifacts_path.mkdir(parents=True, exist_ok=True)

    click.echo(f"Running {suite} tests...")

    runner = TestRunner(suite=suite, parallel=parallel, artifacts_dir=artifacts_path)
    exit_code = runner.run()

    if exit_code == 0:
        click.echo(click.style("All tests passed!", fg="green"))
    else:
        click.echo(click.style(f"Tests failed (exit code: {exit_code})", fg="red"))

    sys.exit(exit_code)


@main.command()
@click.option("-f", "--file", "spec_file", required=True, help="Path to spec.yml")
@click.option("--remove-volumes/--keep-volumes", default=True, help="Remove volumes")
def down(spec_file: str, remove_volumes: bool):
    """Stop stack and clean up resources."""
    config = SpecConfig.from_file(spec_file)

    click.echo("Tearing down environment...")

    ansible = AnsibleRunner()
    exit_code = ansible.down(
        compose_file=config.compose_file,
        run_id="cleanup",
        remove_volumes=remove_volumes,
    )

    if exit_code == 0:
        click.echo(click.style("Environment cleaned up!", fg="green"))
    else:
        click.echo(click.style("Cleanup had issues", fg="yellow"))

    sys.exit(exit_code)


@main.command()
@click.option("-f", "--file", "spec_file", required=True, help="Path to spec.yml")
@click.option("--suite", default="all", help="Test suite: smoke, regression, or all")
@click.option("--parallel", "-n", type=int, help="Number of parallel workers")
@click.option("--artifacts-dir", type=click.Path(), help="Artifacts directory")
@click.option("--timeout", type=int, help="Readiness timeout in seconds")
@click.option("--keep-on-fail", is_flag=True, help="Don't tear down on failure")
def run(
    spec_file: str,
    suite: str,
    parallel: int | None,
    artifacts_dir: str | None,
    timeout: int | None,
    keep_on_fail: bool,
):
    """Run full E2E workflow: up + test + down."""
    config = SpecConfig.from_file(spec_file)
    run_id = generate_run_id()

    artifacts_path = Path(artifacts_dir) if artifacts_dir else Path("artifacts") / run_id
    artifacts_path.mkdir(parents=True, exist_ok=True)

    reporter = Reporter(run_id, artifacts_path)
    reporter.mark_start()

    ansible = AnsibleRunner()
    final_exit_code = 0
    should_teardown = True

    click.echo(f"Starting E2E run (run_id: {run_id})...")
    click.echo(f"Artifacts: {artifacts_path}")

    # Step 1: Bring up environment
    click.echo("\n[1/3] Starting environment...")
    health_checks = [c.model_dump() for c in config.get_health_checks()]

    up_exit = ansible.up(
        compose_file=config.compose_file,
        run_id=run_id,
        health_checks=health_checks,
        timeout_secs=timeout or config.timeout,
        env_file=config.env_file,
    )

    if up_exit != 0:
        click.echo(click.style("Environment startup failed!", fg="red"))
        final_exit_code = 2
        ansible.collect_artifacts(
            compose_file=config.compose_file,
            run_id=run_id,
            artifacts_dir=str(artifacts_path),
            services=config.services,
        )
        reporter.write_summary(final_exit_code)
        if not keep_on_fail:
            ansible.down(config.compose_file, run_id)
        sys.exit(final_exit_code)

    reporter.mark_env_ready()
    click.echo(click.style("Environment ready!", fg="green"))

    # Step 2: Run tests
    click.echo(f"\n[2/3] Running {suite} tests...")
    runner = TestRunner(suite=suite, parallel=parallel, artifacts_dir=artifacts_path)
    test_exit = runner.run()
    reporter.mark_test_end()

    if test_exit != 0:
        click.echo(click.style("Tests failed!", fg="red"))
        final_exit_code = 1
        if keep_on_fail:
            should_teardown = False
            click.echo("Keeping environment up for debugging (--keep-on-fail)")

    # Collect artifacts
    collect_mode = config.artifacts.collect
    if final_exit_code != 0 or collect_mode == "always":
        click.echo("\nCollecting artifacts...")
        ansible.collect_artifacts(
            compose_file=config.compose_file,
            run_id=run_id,
            artifacts_dir=str(artifacts_path),
            services=config.services,
        )

    # Write summary
    reporter.write_summary(final_exit_code)

    # Step 3: Tear down
    if should_teardown:
        click.echo("\n[3/3] Tearing down environment...")
        ansible.down(config.compose_file, run_id)
        click.echo(click.style("Cleanup complete!", fg="green"))

    # Final summary
    click.echo(f"\n{'='*50}")
    if final_exit_code == 0:
        click.echo(click.style("E2E run completed successfully!", fg="green", bold=True))
    else:
        click.echo(
            click.style(f"E2E run failed (exit code: {final_exit_code})", fg="red", bold=True)
        )
    click.echo(f"Artifacts: {artifacts_path}")

    sys.exit(final_exit_code)


@main.command()
@click.option("-f", "--file", "spec_file", required=True, help="Path to spec.yml")
def status(spec_file: str):
    """Show container states and health."""
    config = SpecConfig.from_file(spec_file)

    ansible = AnsibleRunner()
    exit_code = ansible.status(config.compose_file)
    sys.exit(exit_code)


@main.command()
@click.option("-f", "--file", "spec_file", required=True, help="Path to spec.yml")
@click.option("--service", help="Specific service to show logs for")
def logs(spec_file: str, service: str | None):
    """Show logs from running containers."""
    config = SpecConfig.from_file(spec_file)

    import subprocess

    cmd = ["docker", "compose", "-f", config.compose_file, "logs"]
    if service:
        cmd.append(service)
    cmd.append("--no-color")

    subprocess.run(cmd)


if __name__ == "__main__":
    main()
