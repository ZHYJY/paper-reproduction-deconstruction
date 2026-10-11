#!/usr/bin/env python3
"""Run reproducibility commands from a JSON manifest and preserve auditable logs."""
from __future__ import annotations
import argparse, hashlib, json, os, platform, shlex, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

def digest(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def snapshot(cwd: Path) -> dict:
    return {"time_utc": datetime.now(timezone.utc).isoformat(), "cwd": str(cwd),
            "python": sys.version, "executable": sys.executable,
            "platform": platform.platform()}

def safe_run_id(value: str) -> str:
    if not value or value in {".", ".."} or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for ch in value):
        raise ValueError(f"invalid run id: {value!r}")
    return value

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("manifest", type=Path)
    p.add_argument("-o", "--output-root", type=Path, default=Path("artifacts/runs"))
    p.add_argument("--allow-failure", action="store_true")
    p.add_argument("--dry-run", action="store_true",
                   help="校验 manifest 并打印将要运行的命令，不执行任何进程")
    p.add_argument("--job", type=str, default=None,
                   help="只运行指定 run id（可重复传入）")
    args = p.parse_args()
    manifest_path = args.manifest.resolve()
    spec = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    project_root_value = Path(spec.get("project_root", "."))
    root = (project_root_value if project_root_value.is_absolute() else manifest_path.parent / project_root_value).resolve()
    if not isinstance(spec.get("runs"), list) or not spec["runs"]:
        p.error("manifest must contain a non-empty runs list")
    out_root = args.output_root.resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    selected = spec["runs"]
    if args.job:
        wanted = set(args.job.split(","))
        selected = [item for item in selected if str(item.get("id")) in wanted]
        if not selected:
            p.error(f"no run matches --job {args.job!r}")
    results = []
    any_failed = False
    ran_any = False
    for item in selected:
        run_id = safe_run_id(str(item.get("id", "")))
        command = item.get("cmd")
        use_shell = bool(item.get("shell", False))
        if use_shell:
            if not isinstance(command, str):
                raise ValueError(f"{run_id}: shell=true requires string cmd")
            display_command = command
        else:
            if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
                raise ValueError(f"{run_id}: cmd must be a non-empty string list unless shell=true")
            display_command = shlex.join(command)
        cwd = (root / item.get("cwd", ".")).resolve()
        if (root not in cwd.parents) and (cwd != root):
            raise ValueError(f"{run_id}: cwd must be inside project_root")
        if args.dry_run:
            print(f"[dry-run] {run_id}: cwd={cwd} shell={use_shell} timeout={item.get('timeout_sec', 3600)}")
            print(f"           $ {display_command}")
            continue
        run_dir = out_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        for key, value in (item.get("env") or {}).items():
            env[str(key)] = str(value)
        started = time.time()
        started_at = datetime.now(timezone.utc).isoformat()
        timeout = float(item.get("timeout_sec", 3600))
        try:
            proc = subprocess.run(command, cwd=cwd, env=env, shell=use_shell,
                                  capture_output=True, text=True, timeout=timeout)
            timed_out = False
            returncode = proc.returncode
            stdout, stderr = proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            returncode = None
            stdout = exc.stdout or ""
            stderr = (exc.stderr or "") + f"\nTimed out after {timeout} seconds.\n"
        ended_at = datetime.now(timezone.utc).isoformat()
        elapsed = time.time() - started
        (run_dir / "stdout.txt").write_text(stdout, encoding="utf-8", errors="replace")
        (run_dir / "stderr.txt").write_text(stderr, encoding="utf-8", errors="replace")
        outputs = []
        for rel in item.get("outputs", []) or []:
            path = (root / rel).resolve()
            if root not in path.parents and path != root:
                raise ValueError(f"{run_id}: output escapes project_root: {rel}")
            outputs.append({"path": path.relative_to(root).as_posix(), "exists": path.exists(), "sha256": digest(path)})
        result = {"id": run_id, "cmd": command, "display_cmd": display_command, "shell": use_shell,
                  "cwd": str(cwd), "started_utc": started_at, "ended_utc": ended_at,
                  "elapsed_sec": round(elapsed, 6), "timeout_sec": timeout,
                  "returncode": returncode, "timed_out": timed_out, "ok": returncode == 0,
                  "seed": item.get("seed"), "outputs": outputs,
                  "environment": snapshot(cwd)}
        (run_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        results.append(result)
        ran_any = True
        if not result["ok"]:
            any_failed = True
    if not ran_any:
        return 0
    summary = {"manifest": str(manifest_path), "generated_utc": datetime.now(timezone.utc).isoformat(),
               "project_root": str(root), "runs": results, "ok": not any_failed}
    (out_root / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if (not any_failed or args.allow_failure) else 1

if __name__ == "__main__":
    raise SystemExit(main())
