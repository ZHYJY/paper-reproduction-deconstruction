#!/usr/bin/env python3
"""Extract text and figure/table captions from a PDF into a JSON audit file.

Backend priority (first available wins):
  1. pdfplumber (best layout/caption fidelity)
  2. pypdf / PyPDF2
  3. pdftotext (poppler command line; needs binary on PATH)

Output JSON (or --format txt for a flat text dump):
  {"pdf": path, "pages": N, "backend": "...", "per_page": [
     {"page": 1, "text": "...", "captions": ["Fig. 2: ...", ...]}], "captions_all": [...]}

Caption detection is heuristic (Fig./Figure/Table/图/表 at line start); never
treat it as authoritative for content claims — always re-check the page text.
"""
from __future__ import annotations
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path

CAPTION_RE = re.compile(
    r"^\s*(?:Fig(?:ure)?s?\.?\s*\d|Table\s*\d|图\s*\d|表\s*\d|Algorithm\s*\d)",
    re.IGNORECASE,
)


def extract_pdfplumber(path: Path) -> list[dict]:
    import pdfplumber  # type: ignore
    pages = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append({"page": page.page_number, "text": text})
    return pages


def extract_pypdf(path: Path) -> list[dict]:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        from PyPDF2 import PdfReader  # type: ignore
    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append({"page": i, "text": text})
    return pages


def extract_pdftotext(path: Path) -> list[dict]:
    result = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                            capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"pdftotext failed: {result.stderr[:300]}")
    raw = result.stdout
    # pdftotext does not give page boundaries; split on form feeds.
    chunks = [c for c in raw.split("\f") if c.strip()]
    return [{"page": i, "text": c} for i, c in enumerate(chunks, start=1)]


def pick_backend(path: Path) -> tuple[str, list[dict]]:
    for name, fn in (("pdfplumber", extract_pdfplumber),
                     ("pypdf/PyPDF2", extract_pypdf),
                     ("pdftotext", extract_pdftotext)):
        if name == "pdftotext" and shutil.which("pdftotext") is None:
            continue
        if name != "pdftotext":
            try:
                __import__("pdfplumber" if name == "pdfplumber" else "pypdf")
            except ImportError:
                try:
                    __import__("PyPDF2")
                except ImportError:
                    continue
        try:
            pages = fn(path)
            if pages:
                return name, pages
        except Exception as exc:  # backend-specific failure: try next one
            print(f"[extract_pdf] backend {name} failed: {exc}", file=sys.stderr)
    raise RuntimeError(
        "no PDF text backend available. Install one of: "
        "pip install pdfplumber  |  pip install pypdf  |  add poppler-utils (pdftotext) to PATH"
    )


def captions_from(pages: list[dict]) -> tuple[list[str], list[dict]]:
    all_captions = []
    per_page = []
    for page in pages:
        found = []
        for line in page["text"].splitlines():
            if CAPTION_RE.match(line):
                found.append(line.strip())
        all_captions.extend(found)
        per_page.append({**page, "captions": found})
    return all_captions, per_page


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("pdf", type=Path)
    p.add_argument("-o", "--output", type=Path, default=None,
                   help="输出 JSON 路径（默认 stdout）")
    p.add_argument("--format", dest="fmt", choices=["json", "txt"], default="json",
                   help="txt=纯文本全文拼接（便于检索）")
    p.add_argument("--backend", choices=["pdfplumber", "pypdf", "pdftotext"],
                   default=None, help="强制指定后端")
    args = p.parse_args()
    path = args.pdf.resolve()
    if not path.is_file():
        p.error(f"not a file: {path}")

    if args.backend:
        table = {"pdfplumber": extract_pdfplumber, "pypdf": extract_pypdf,
                 "pdftotext": extract_pdftotext}
        pages = table[args.backend](path)
        backend = args.backend
    else:
        backend, pages = pick_backend(path)

    all_captions, per_page = captions_from(pages)
    doc = {
        "pdf": str(path),
        "backend": backend,
        "pages": len(pages),
        "caption_count": len(all_captions),
        "per_page": per_page,
        "captions_all": all_captions,
    }
    if args.fmt == "txt":
        text = "\n\n".join(f"[page {page['page']}]\n{page['text']}" for page in pages)
        if args.output:
            args.output.write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
        return 0
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
