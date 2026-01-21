# AutoE2E Lab

One-command E2E testing with containerized environments using Ansible orchestration.

## Quick Start

### On Linux/macOS
```bash
pip install -e .
ansible-galaxy collection install community.docker
autoe2e run -f demo/spec.yml
```

### On Windows (requires WSL)
Ansible doesn't run natively on Windows. Use WSL:

```bash
# 1. Open WSL terminal
wsl

# 2. Install Python and pip in WSL
sudo apt update && sudo apt install python3-pip python3-venv

# 3. Create venv and install
python3 -m venv venv
source venv/bin/activate
pip install -e .
ansible-galaxy collection install community.docker

# 4. Run (Docker Desktop must have WSL integration enabled)
autoe2e run -f demo/spec.yml
```

## Commands

| Command | Description |
|---------|-------------|
| `autoe2e up -f spec.yml` | Start Docker Compose stack |
| `autoe2e test -f spec.yml` | Run E2E tests |
| `autoe2e down -f spec.yml` | Stop and clean up |
| `autoe2e run -f spec.yml` | Full workflow: up → test → down |
| `autoe2e status -f spec.yml` | Show container states |
| `autoe2e logs -f spec.yml` | View container logs |

## CLI Options

```
--suite smoke|regression|all    Test suite to run
--parallel N                    Run tests in parallel (pytest-xdist)
--artifacts-dir PATH            Where to store artifacts
--timeout SEC                   Readiness timeout
--keep-on-fail                  Don't tear down on failure
```

## Configuration (spec.yml)

```yaml
compose_file: docker-compose.yml
base_url: http://localhost:8080

health_checks:
  - type: http
    url: http://localhost:8080/health
    expected_status: 200
  - type: tcp
    host: localhost
    port: 5432

suites:
  smoke: smoke
  regression: regression

timeout: 120

artifacts:
  collect: on_fail  # on_fail | always
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Test failures |
| 2 | Environment/setup failure |

## Artifacts Structure

```
artifacts/<run_id>/
├── logs/
│   └── all.log           # Container logs
├── reports/
│   ├── junit.xml         # JUnit XML for CI
│   └── summary.json      # Run summary
├── env/
│   ├── metadata.json     # Docker versions
│   └── container_states.txt
└── compose/
    └── docker-compose.yml
```

## Demo Stack

The included demo has:
- FastAPI application with CRUD endpoints
- PostgreSQL database
- Redis cache

```bash
# Run smoke tests only
autoe2e run -f demo/spec.yml --suite smoke

# Run with debugging on failure
autoe2e run -f demo/spec.yml --keep-on-fail
```

## Requirements

- Python 3.11+
- Docker with Compose v2
- Ansible 2.15+ (runs on Linux/macOS/WSL)

## CI Integration

GitHub Actions workflow included. JUnit XML output is automatically parsed for test reporting.
can y