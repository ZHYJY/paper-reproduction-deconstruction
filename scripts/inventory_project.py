#!/usr/bin/env python3
"""Create a deterministic inventory and SHA-256 manifest for a paper/code project."""
from __future__ import annotations
import argparse, hashlib, json, mimetypes, os, platform, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone

CATEGORIES = {
    "paper": {".pdf", ".tex", ".bib", ".docx", ".odt", ".html", ".htm"},
    "code": {".py", ".r", ".rmd", ".jl", ".m", ".ipynb", ".sh", ".bash", ".js", ".ts", ".java", ".cpp", ".c", ".h"},
    "config": {".yaml", ".yml", ".json", ".toml", ".ini", ".cfg", ".env"},
    "data": {".csv", ".tsv", ".parquet", ".feather", ".pkl", ".pickle", ".h5", ".hdf5", ".npz", ".npy"},
    "model": {".pt", ".pth", ".ckpt", ".onnx", ".safetensors", ".bin"},
    "media": {".png", ".jpg", ".jpeg", ".svg", ".eps", ".gif", ".mp4"},
}
DEFAULT_IGNORES = {".git", ".venv", "venv", "__pycache__", "node_modules", "build", "dist"}

def sha256(path: Path, chunk: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(chunk), b""):
            digest.update(block)
    return digest.hexdigest()

def category(path: Path) -> str:
    suffix = path.suffix.lower()
    for name, suffixes in CATEGORIES.items():
        if suffix in suffixes:
            return name
    return "other"

def git_commit(root: Path) -> str | None:
    try:
        value = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL)
        return value.strip()
    except (OSError, subprocess.CalledProcessError):
        return None

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("-o", "--output", type=Path, default=None)
    parser.add_argument("--include-hidden", action="store_true")
    parser.add_argument("--no-git", action="store_true", help="跳过 git commit 探测")
    parser.add_argument("--format", dest="fmt", choices=["json", "md"], default="json",
                        help="json=机器可读清单（默认）；md=Markdown 清单表")
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        parser.error(f"root is not a directory: {root}")
    entries = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel_parts = path.relative_to(root).parts
        if any(part in DEFAULT_IGNORES for part in rel_parts):
            continue
        if not args.include_hidden and any(part.startswith(".") for part in rel_parts):
            continue
        stat = path.stat()
        entries.append({
            "path": path.relative_to(root).as_posix(),
            "category": category(path),
            "size_bytes": stat.st_size,
            "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "mime": mimetypes.guess_type(path.name)[0],
            "sha256": sha256(path),
        })
    by_category = {}
    for entry in entries:
        by_category[entry["category"]] = by_category.get(entry["category"], 0) + 1
    manifest = {
        "root": str(root),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "git_commit": None if args.no_git else git_commit(root),
        "file_count": len(entries),
        "count_by_category": by_category,
        "files": entries,
    }
    if args.fmt == "md":
        lines = [
            f"# 材料清单：{root}",
            "",
            f"- 生成时间：{manifest['generated_utc']}",
            f"- 文件总数：{manifest['file_count']}",
            f"- 分类统计：" + ", ".join(f"{k}={v}" for k, v in sorted(by_category.items())),
            f"- Python：{sys.version.split()[0]} / {platform.platform()}",
            f"- Git commit：{manifest['git_commit'] or '未检测'}",
            "",
            "| 路径 | 类别 | 大小(B) | SHA-256 |",
            "| --- | --- | --- | --- |",
        ]
        for entry in entries:
            lines.append(f"| {entry['path'].replace('|', '\\|')} | {entry['category']} | "
                         f"{entry['size_bytes']} | `{entry['sha256'][:16]}…` |")
        payload = "\n".join(lines) + "\n"
    else:
        payload = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
