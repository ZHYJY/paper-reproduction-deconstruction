#!/usr/bin/env python3
"""Generate a from-scratch reproduction checklist from run results.

Inputs:
- artifacts/runs/summary.json (produced by run_manifest.py)
- the original repro_manifest.json

Output: a Markdown checklist that another researcher can replay, with the
exact commands, seeds, hashes and known gaps. Use it to fill report §11
(局限与下一步 → 复现清单).

    python scripts/make_repro_checklist.py artifacts/runs/summary.json repro_manifest.json -o artifacts/repro_checklist.md
"""
from __future__ import annotations
import argparse, json
from pathlib import Path


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("summary", type=Path, help="run_manifest.py 输出的 summary.json")
    p.add_argument("manifest", type=Path, help="原始 repro_manifest.json")
    p.add_argument("-o", "--output", type=Path, default=None)
    args = p.parse_args()
    summary = read_json(args.summary.resolve())
    manifest = read_json(args.manifest.resolve())

    runs = {r["id"]: r for r in summary.get("runs", [])}
    lines = [
        "# 复现清单（从零重放）",
        "",
        f"- 生成时间：{summary.get('generated_utc', '?')}",
        f"- 项目根：`{summary.get('project_root', '?')}`",
        f"- 总状态：{'通过' if summary.get('ok') else '存在失败/异常运行'}",
        "",
        "## 0. 环境准备",
        "- [ ] 安装 Python 版本与依赖（见 `artifacts/env/environment.before.json` / `pip freeze`）",
        "- [ ] 下载数据与 checkpoint，记录 URL、访问日期、SHA-256",
        "- [ ] 固定随机种子与 `PYTHONHASHSEED`",
        "",
        "## 1. 逐项运行",
        "",
        "| run | 命令 | 目录 | 种子 | 超时(s) | 状态 | 日志 | 输出哈希 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in manifest.get("runs", []):
        run_id = str(item.get("id", ""))
        r = runs.get(run_id, {})
        status = "ok" if r.get("ok") else ("timeout" if r.get("timed_out") else "failed")
        cmd = item.get("cmd")
        if isinstance(cmd, list):
            cmd_text = " ".join(cmd)
        else:
            cmd_text = str(cmd)
        outputs = r.get("outputs", [])
        out_text = "; ".join(f"`{o['path']}` {o['sha256'][:10] if o['sha256'] else '缺失'}"
                             for o in outputs) if outputs else "-"
        lines.append(
            f"| `{run_id}` | `{cmd_text.replace('|', '\\|')}` | `{r.get('cwd', item.get('cwd', '.'))}` | "
            f"{item.get('seed', '-')} | {item.get('timeout_sec', 3600)} | {status} | "
            f"`artifacts/runs/{run_id}/` | {out_text} |")
        if status != "ok":
            lines.append(f"  - [ ] 诊断 `{run_id}` 失败：见 `artifacts/runs/{run_id}/stderr.txt`")

    lines += [
        "",
        "## 2. 数值核对",
        "- [ ] 用 `scripts/compare_numbers.py --key-column <主键> 论文值.csv 复现值.csv` 重跑逐元素比较",
        "- [ ] 确认 pass/fail/missing 计数与报告 §8 一致",
        "",
        "## 3. 已知缺口（如实填写）",
        "- [ ] 未验证：_（外部数据、附录定理等）_",
        "- [ ] 阻塞项：_（硬件、网络、许可证）_",
        "- [ ] 已排除原因：_（见差异诊断）_",
        "",
        "## 4. 验收",
        "- [ ] 主结果与至少一个边界/消融结果在声明容差内一致",
        "- [ ] 报告中的每个数字可回溯到运行日志或输出文件",
    ]
    text = "\n".join(lines) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
