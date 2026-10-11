#!/usr/bin/env python3
"""Convert a nested mindmap JSON document to Mermaid mindmap syntax.

Node labels frequently carry evidence back-references such as [§3] or [C01].
Those brackets and other punctuation conflict with Mermaid's shape syntax, so
labels are auto-quoted with double quotes whenever they contain special
characters. Verify the result by rendering in Mermaid (or at least grep the
output for unbalanced quotes).
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

# Characters that break Mermaid mindmap shape parsing when unquoted.
_UNSAFE = re.compile(r'[\[\](){}#"<>]')

def clean(label) -> str:
    return " ".join(str(label).replace("\n", " ").split())

def quote(label: str) -> str:
    """Wrap in double quotes when the label contains Mermaid-special chars."""
    if _UNSAFE.search(label):
        return '"' + label.replace('"', '\\"') + '"'
    return label

def emit(node, depth, lines):
    label = clean(node.get("label", ""))
    if not label:
        raise ValueError("every node needs a non-empty label")
    lines.append("  " * depth + quote(label))
    for child in node.get("children", []) or []:
        emit(child, depth + 1, lines)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("input", type=Path)
    p.add_argument("-o", "--output", type=Path)
    args = p.parse_args()
    doc = json.loads(args.input.read_text(encoding="utf-8-sig"))
    title = clean(doc.get("title", ""))
    if not title:
        raise SystemExit("input needs a non-empty title")
    lines = ["mindmap", "  root((" + quote(title) + "))"]
    for branch in doc.get("branches", []) or []:
        emit(branch, 2, lines)
    text = "\n".join(lines) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")

if __name__ == "__main__":
    main()
