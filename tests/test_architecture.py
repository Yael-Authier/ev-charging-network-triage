"""Architectural guards.

Rules that are easy to state and easy to break silently, so they are enforced by
tests rather than by documentation.

Block 4 will add the file-level ground-truth leakage guard to this same file.
"""

from __future__ import annotations

import re

IMPORT_GENERATOR = re.compile(r"^\s*(?:from\s+generator(?:\.\w+)*\s+import\b|import\s+generator\b)")
IMPORT_SRC = re.compile(r"^\s*(?:from\s+src(?:\.\w+)*\s+import\b|import\s+src\b)")
DYNAMIC_IMPORT = re.compile(r"import_module\(\s*[\"']([\w.]+)")


def _offending_lines(root, pattern, dynamic_target):
    """Return `path:line: text` for every import of `dynamic_target` under root."""
    offenders: list[str] = []
    for path in sorted(root.rglob("*.py")):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            hit = pattern.match(line)
            dynamic = DYNAMIC_IMPORT.search(line)
            if hit or (dynamic and dynamic.group(1).split(".")[0] == dynamic_target):
                offenders.append(f"{path.name}:{lineno}: {line.strip()}")
    return offenders


def test_src_never_imports_generator(repo_root):
    """The analytical layer must not depend on the generator.

    `src/` reads `data/observed/`. If it could import `generator`, it would have
    a direct path to latent configuration and to ground-truth builders, and the
    information boundary would rest on discipline alone.
    """
    offenders = _offending_lines(repo_root / "src", IMPORT_GENERATOR, "generator")
    assert offenders == [], (
        "src/ must never import generator/. Offending lines:\n" + "\n".join(offenders)
    )


def test_generator_never_imports_src(repo_root):
    """And the reverse, to keep the dependency acyclic.

    The generator does not need analytical code. Allowing the import would make
    it possible for a derived analytical feature to feed back into the world,
    which is exactly the kind of circularity the backtest cannot survive.
    """
    offenders = _offending_lines(repo_root / "generator", IMPORT_SRC, "src")
    assert offenders == [], (
        "generator/ must never import src/. Offending lines:\n" + "\n".join(offenders)
    )