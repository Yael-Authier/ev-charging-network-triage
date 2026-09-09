"""Task runner for this repository.

Usage:  python tasks.py <target>
Cross-platform on purpose: no `make` required, so the project runs on any
machine with Python installed.
"""

from __future__ import annotations

import subprocess
import sys

REPO_TARGETS = {
    "check": "Run the test suite",
    "data": "Generate the synthetic dataset (not implemented yet)",
    "db": "Build the DuckDB warehouse from generated data (not implemented yet)",
    "app": "Launch the Streamlit decision app (not implemented yet)",
    "all": "data -> db -> check (not implemented yet)",
}

NOT_IMPLEMENTED = {
    "data": "generator/generate.py does not exist yet (block 2-3).",
    "db": "sql/ layer does not exist yet (block 5).",
    "app": "app/streamlit_app.py does not exist yet (block 10).",
    "all": "Pipeline is incomplete; run `python tasks.py check` for now.",
}


def run(command: list[str]) -> int:
    """Run a command and return its exit code."""
    print(f"$ {' '.join(command)}")
    return subprocess.call(command)


def task_check() -> int:
    """Run pytest over the repository."""
    return run([sys.executable, "-m", "pytest", "-q"])


def usage() -> None:
    print(__doc__)
    print("Targets:")
    width = max(len(name) for name in REPO_TARGETS)
    for name, description in REPO_TARGETS.items():
        print(f"  {name.ljust(width)}  {description}")


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] in {"-h", "--help", "--list"}:
        usage()
        return 0

    target = argv[1]

    if target == "check":
        return task_check()

    if target in NOT_IMPLEMENTED:
        print(f"Target '{target}' is not available yet: {NOT_IMPLEMENTED[target]}")
        return 1

    print(f"Unknown target '{target}'.\n")
    usage()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))