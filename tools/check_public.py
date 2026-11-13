"""Offline integrity/syntax/link check for the curated public export; no imports of device code."""
import ast
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = "evidence/public-files.json"


def main():
    rows = json.loads((ROOT / MANIFEST).read_text(encoding="utf-8"))["files"]
    expected = {row["path"] for row in rows} | {MANIFEST}
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
              if p.is_file() and not any(part in {".git", "__pycache__"} for part in p.relative_to(ROOT).parts)}
    if actual != expected:
        raise ValueError(f"Export inventory differs: extra={sorted(actual-expected)}, missing={sorted(expected-actual)}")
    for row in rows:
        path = ROOT / row["path"]
        if not path.resolve().is_relative_to(ROOT) or path.is_symlink():
            raise ValueError("Outside export or symbolic link: " + row["path"])
        data = path.read_bytes()
        if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise ValueError("Changed export file: " + row["path"])
        if path.suffix == ".py":
            ast.parse(data, filename=row["path"])
        if path.suffix == ".md":
            for target in re.findall(r"!?\[[^\]]*\]\(([^\s)]+)\)", data.decode("utf-8")):
                if target.startswith(("https://", "http://", "#", "mailto:")):
                    continue
                linked = (path.parent / unquote(target.split("#", 1)[0])).resolve()
                if not linked.is_relative_to(ROOT) or not linked.exists():
                    raise ValueError(f"Broken or external local link in {row['path']}: {target}")
    print(f"PUBLIC_EXPORT_OK: {len(rows)} files; hashes, syntax and local links checked; no camera access.")


if __name__ == "__main__":
    main()
