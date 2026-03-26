from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "SIGNATURE.sha256"

# Keep a stable, reviewable manifest scope for release integrity checks.
SIGNED_FILES = [
    "README.md",
    "README_EN.md",
    "CHANGELOG.md",
    "BLOCKCHAIN_INFO.md",
    "PHAM_BLOCKCHAIN_LOG.md",
    "pyproject.toml",
    "VERSION",
    "sensory_input_kernel/__init__.py",
    "sensory_input_kernel/sensory_kernel.py",
    "sensory_input_kernel/bridge/mpk_bridge.py",
    "sensory_input_kernel/runtime/edge_loop.py",
    "sensory_input_kernel/runtime/daemon_cli.py",
    "tests/test_sensory_input_kernel.py",
    "tests/conftest.py",
    "scripts/verify_signature.py",
    "scripts/generate_signature.py",
]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    lines = []
    for rel in SIGNED_FILES:
        target = ROOT / rel
        if not target.exists():
            raise FileNotFoundError(f"missing signed file: {rel}")
        lines.append(f"{sha256_of(target)}  {rel}")
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"updated {MANIFEST.name} with {len(lines)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

