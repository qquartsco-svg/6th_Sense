from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "SIGNATURE.sha256"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    if not MANIFEST.exists():
        print("SIGNATURE.sha256: missing")
        return 1

    ok = True
    for raw in MANIFEST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        digest, relpath = line.split("  ", 1)
        target = ROOT / relpath
        if not target.exists():
            print(f"MISSING {relpath}")
            ok = False
            continue
        current = sha256_of(target)
        if current != digest:
            print(f"MISMATCH {relpath}")
            ok = False
            continue
        print(f"OK {relpath}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
