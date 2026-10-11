#!/usr/bin/env python3
"""Compare numeric leaves in JSON or CSV and report tolerance-aware differences.

CSV 行为对齐：
- 默认按行序拍平（旧行为，适合行序与行数一致的输出）；
- 传入 --key-column <col> 时，两个 CSV 都按该列建立 {key: row} 索引后再逐行
  比较，行序不同或行数不同也不会错位；key 缺失的行记为 missing。

输出：
- 默认 JSON 摘要（含 pass/fail/missing 计数）；
- --format md 输出可直接粘贴进复现报告的结果对照表。
"""
from __future__ import annotations
import argparse, csv, json, math
from pathlib import Path


def number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if not s or s.lower() in {"nan", "na", "null", "none", "-", "--"}:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def flatten(value, prefix=""):
    out = {}
    n = number(value)
    if n is not None:
        out[prefix or "$"] = n
    elif isinstance(value, dict):
        for k, v in value.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(value, list):
        for i, v in enumerate(value):
            out.update(flatten(v, f"{prefix}[{i}]"))
    return out


def load_csv(path: Path, key_column: str | None):
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if key_column is None:
        return flatten(rows)
    keyed = {}
    for row in rows:
        key = str(row.get(key_column, "")).strip()
        if not key:
            raise ValueError(f"{path.name}: --key-column {key_column!r} has empty values")
        if key in keyed:
            raise ValueError(f"{path.name}: duplicate key {key!r} in --key-column {key_column!r}")
        keyed[key] = {k: v for k, v in row.items() if k != key_column}
    return keyed


def expand_keyed(keyed: dict) -> dict:
    """Expand {key: {col: val}} into numeric leaves.

    Single numeric column per key -> flat key (most common metrics table).
    Multiple numeric columns     -> key like 'acc.paper' / 'acc.repro'.
    """
    flat = {}
    for key, row in keyed.items():
        nums = [(col, n) for col, n in ((c, number(v)) for c, v in row.items()) if n is not None]
        if len(nums) == 1:
            flat[key] = nums[0][1]
        else:
            for col, n in nums:
                flat[f"{key}.{col}"] = n
    return flat


def load(path: Path, key_column: str | None):
    if path.suffix.lower() == ".csv":
        loaded = load_csv(path, key_column)
        return (expand_keyed(loaded) if key_column else loaded), key_column
    if key_column is not None:
        raise ValueError("--key-column only applies to CSV inputs")
    return flatten(json.loads(path.read_text(encoding="utf-8-sig"))), None


def format_float(value, width=6):
    if value is None:
        return "-"
    if value == math.inf:
        return "inf"
    text = f"{value:.{width}g}"
    return text


def main():
    p = argparse.ArgumentParser()
    p.add_argument("reference", type=Path)
    p.add_argument("reproduced", type=Path)
    p.add_argument("--atol", type=float, default=1e-8)
    p.add_argument("--rtol", type=float, default=1e-5)
    p.add_argument("--key-column", type=str, default=None,
                   help="CSV 主键列名，按该列对齐两个文件的行（推荐）")
    p.add_argument("--format", dest="fmt", choices=["json", "md"], default="json",
                   help="json=机器可读摘要（默认）；md=Markdown 对照表")
    p.add_argument("-o", "--output", type=Path)
    args = p.parse_args()

    ref, _ = load(args.reference, args.key_column)
    got, _ = load(args.reproduced, args.key_column)

    keys = sorted(set(ref) | set(got))
    rows = []
    for key in keys:
        a = ref.get(key)
        b = got.get(key)
        if a is None or b is None:
            rows.append({"key": key, "reference": a, "reproduced": b,
                         "abs_diff": None, "rel_diff": None, "limit": None,
                         "status": "missing"})
            continue
        diff = abs(b - a)
        rel = diff / abs(a) if a != 0 else (0.0 if diff == 0 else math.inf)
        limit = args.atol + args.rtol * abs(a)
        rows.append({"key": key, "reference": a, "reproduced": b,
                     "abs_diff": diff, "rel_diff": rel, "limit": limit,
                     "status": "pass" if diff <= limit else "fail"})

    counts = {
        "pass": sum(r["status"] == "pass" for r in rows),
        "fail": sum(r["status"] == "fail" for r in rows),
        "missing": sum(r["status"] == "missing" for r in rows),
        "total": len(rows),
    }
    summary = {
        "reference": str(args.reference),
        "reproduced": str(args.reproduced),
        "key_column": args.key_column,
        "atol": args.atol,
        "rtol": args.rtol,
        "counts": counts,
        "items": rows,
    }

    if args.fmt == "md":
        lines = [
            "| key | paper | reproduced | abs_diff | rel_diff | limit | status |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for r in rows:
            lines.append("| {key} | {ref} | {got} | {ad} | {rd} | {lim} | {st} |".format(
                key=r["key"].replace("|", "\\|"),
                ref=format_float(r["reference"]),
                got=format_float(r["reproduced"]),
                ad=format_float(r["abs_diff"]),
                rd="inf" if r["rel_diff"] == math.inf else format_float(r["rel_diff"]),
                lim=format_float(r["limit"]),
                st=r["status"]))
        lines.append("")
        lines.append(f"> 容差 atol={args.atol:g}, rtol={args.rtol:g}；"
                     f"pass={counts['pass']}, fail={counts['fail']}, missing={counts['missing']}, total={counts['total']}")
        text = "\n".join(lines) + "\n"
    else:
        text = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"

    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if counts["fail"] == 0 and counts["missing"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
