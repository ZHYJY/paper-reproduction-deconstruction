#!/usr/bin/env python3
"""Snapshot the runtime environment before/after a reproduction run.

Collects OS, CPU/RAM, GPU (nvidia-smi if present), Python, key package
versions and the full pip freeze. Save with a stage label so a run's
before/after snapshots are distinguishable:

    python scripts/snapshot_env.py -o artifacts/env/environment.before.json
    ... run ...
    python scripts/snapshot_env.py -o artifacts/env/environment.after.json

pip freeze can be slow in large environments; pass --skip-pip to omit it, or
--pip-limit to keep only the first N lines.
"""
from __future__ import annotations
import argparse, json, os, platform, shutil, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

PIP_TIMEOUT = 120


def run(cmd: list[str], timeout: int = 30) -> str | None:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def pip_freeze(limit: int | None) -> list[str] | None:
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pip", "freeze", "--all"],
            capture_output=True, text=True, timeout=PIP_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    return lines[:limit] if limit else lines


def gpu_info() -> list[dict] | None:
    if shutil.which("nvidia-smi") is None:
        return None
    out = run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
               "--format=csv,noheader,nounits"])
    if not out:
        return None
    infos = []
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 3:
            infos.append({"name": parts[0], "memory_mb": parts[1], "driver": parts[2]})
    return infos


def disk_usage(root: Path) -> dict | None:
    try:
        usage = shutil.disk_usage(root)
        return {"total_bytes": usage.total, "used_bytes": usage.used, "free_bytes": usage.free}
    except OSError:
        return None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("-o", "--output", type=Path, required=True)
    p.add_argument("--skip-pip", action="store_true", help="不采集 pip freeze")
    p.add_argument("--pip-limit", type=int, default=None, help="pip freeze 只保留前 N 行")
    p.add_argument("--label", type=str, default=None, help="阶段标签，如 before/after")
    args = p.parse_args()

    from importlib.metadata import version as _dist_version
    def pkg_version(name: str) -> str | None:
        try:
            return _dist_version(name)
        except Exception:
            return None

    snapshot = {
        "label": args.label,
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "os": platform.platform(),
        "hostname": platform.node(),
        "cpu": platform.processor() or platform.machine(),
        "python": sys.version,
        "executable": sys.executable,
        "key_packages": {name: pkg_version(name) for name in
                         ["torch", "tensorflow", "jax", "numpy", "pandas", "scikit-learn", "scipy"]},
        "gpu": gpu_info(),
        "disk_usage_cwd": disk_usage(Path.cwd()),
        "pip_freeze": None if args.skip_pip else pip_freeze(args.pip_limit),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} ({args.output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
