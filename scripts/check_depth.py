#!/usr/bin/env python3
"""Check whether a deconstruction report meets the default depth standard.

Usage:
    python scripts/check_depth.py path/to/report.md [--json]

Exit code:
    0 if all mandatory checks pass, 1 otherwise.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List

MANDATORY_SECTIONS = [
    ("提示工程", r"提示工程|输入设计|prompt|temperature|system prompt|user prompt"),
    ("经济机制", r"经济机制|理论解释|竞争解释|理论预测|模型假设|命题"),
    ("全表全图映射", r"Table|Figure|代码.*映射|生成脚本|聚合口径"),
    ("代码精读", r"代码精读|核心函数|关键实现|implementation detail"),
    ("数值核对", r"数值核对|结果对照|abs_diff|rel_diff|tolerance"),
    ("局限因果链", r"局限|材料缺失|运行阻塞|实现差异|统计不确定性|外部有效性"),
]

ANTI_SUPERFICIAL_PATTERNS = [
    ("摘要式清单", r"^(作者发现|本文研究|结果表明)[^，。]{0,30}[。]"),
    ("缺失提示工程章节", r"提示工程"),
    ("缺失经济机制章节", r"经济机制|理论解释"),
    ("仅有文件名列", r"^[\s]*\|[^|]+\|\s*[`]?code/[^|]+\|\s*data/[^|]+\|"),
    ("代码无片段", r"```\s*(r|python|bash|julia|cpp|java)"),
    ("数值无逐项", r"abs_diff|rel_diff|tolerance"),
    ("局限一句话", r"数据不可得|无法获取数据|缺少数据"),
]


def read_report(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def check_sections(text: str) -> Dict[str, bool]:
    return {name: bool(re.search(pattern, text, re.IGNORECASE | re.MULTILINE)) for name, pattern in MANDATORY_SECTIONS}


def check_anti_superficial(text: str, report_path: Path) -> Dict[str, bool]:
    # For anti-superficial checks, a PASS means the *good* signal is present.
    # We flip the interpretation for a few.
    checks = {}
    checks["有提示工程章节"] = bool(re.search(r"提示工程|输入设计", text, re.IGNORECASE))
    checks["有经济机制章节"] = bool(re.search(r"经济机制|理论解释", text, re.IGNORECASE))
    checks["Table/Figure 映射含脚本或字段"] = bool(re.search(r"(Table|Figure).*\|.*(`code/|`data/|\.R|\.py|字段|csv|fst)", text, re.IGNORECASE | re.MULTILINE))
    checks["代码含代码片段"] = bool(re.search(r"```\s*(r|python|bash)", text, re.IGNORECASE))
    checks["数值含逐项比较"] = bool(re.search(r"abs_diff|rel_diff|tolerance", text, re.IGNORECASE))
    checks["局限分类型讨论"] = bool(re.search(r"(材料缺失|运行阻塞|实现差异|统计不确定性|外部有效性|数据局限|方法局限|后续方向)", text, re.IGNORECASE))
    checks["思维导图分支足"] = bool(re.search(r"mindmap|思维导图", text, re.IGNORECASE))
    # Accept either report text describing formula explanation in slides, or a slides file exists.
    has_slide_formula_in_report = bool(re.search(r"(slides|幻灯片).*(公式|equation|逐行|解释)", text, re.IGNORECASE | re.DOTALL))
    # Search upward for slides/main.tex
    slides_file = None
    if report_path.name.endswith(".md"):
        for ancestor in [report_path.parent, report_path.parent.parent, report_path.parent.parent.parent]:
            candidate = ancestor / "slides" / "main.tex"
            if candidate.exists():
                slides_file = candidate
                break
    has_slides_file = slides_file.exists() if slides_file else False
    checks["Slides 提及公式解释"] = has_slide_formula_in_report or has_slides_file
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Check deconstruction report depth")
    parser.add_argument("report", type=Path, help="Path to Markdown report")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of text")
    args = parser.parse_args()

    text = read_report(args.report)
    sections = check_sections(text)
    anti = check_anti_superficial(text, args.report)

    section_failures = [name for name, ok in sections.items() if not ok]
    anti_failures = [name for name, ok in anti.items() if not ok]
    passed = not section_failures and not anti_failures

    result = {
        "report": str(args.report),
        "passed": passed,
        "mandatory_sections": sections,
        "anti_superficial_checks": anti,
        "failures": section_failures + anti_failures,
    }

    if args.json:
        import json
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Report: {args.report}")
        print(f"Overall: {'PASS' if passed else 'FAIL'}")
        print("\nMandatory sections:")
        for name, ok in sections.items():
            print(f"  [{'x' if ok else ' '}] {name}")
        print("\nAnti-superficial checks:")
        for name, ok in anti.items():
            print(f"  [{'x' if ok else ' '}] {name}")
        if result["failures"]:
            print("\nFailures:")
            for f in result["failures"]:
                print(f"  - {f}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
