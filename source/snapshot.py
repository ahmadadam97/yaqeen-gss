"""Resolve and verify one complete published run."""
import hashlib
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def definition_digest(path):
    """Ignore line endings, so a definition hashes the same on every checkout."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def build_root():
    return Path(os.environ.get("GSS_BUILD", ROOT / "build")).resolve()


def current_run(build=None):
    build = Path(build) if build is not None else build_root()
    run_id = (build / "LATEST").read_text(encoding="utf8").strip()
    if not re.fullmatch(r"[0-9a-f]{32}", run_id):
        raise ValueError("invalid LATEST run identifier")
    folder = build / "runs" / run_id
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf8"))
    if manifest["run_id"] != run_id:
        raise ValueError("run manifest does not match LATEST")
    for name, expected in manifest["outputs"].items():
        path = (folder / name).resolve()
        if not path.is_relative_to(folder.resolve()) or digest(path) != expected:
            raise ValueError(f"published output changed: {name}")
    requested = os.environ.get("GSS_DB")
    if requested and Path(requested).resolve() != (folder / "gss.duckdb").resolve():
        raise ValueError("GSS_DB differs from published snapshot; unset it and use GSS_BUILD")
    return folder, manifest
