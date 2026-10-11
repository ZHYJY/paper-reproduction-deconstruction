#!/usr/bin/env python3
"""Cross-platform LaTeX Beamer compile + visual QA helper (replaces compile_slides.sh).

Behaviour:
- finds latexmk or xelatex on PATH (Windows included);
- compiles with -interaction=nonstopmode -halt-on-error, logs to build/;
- if pdftoppm or PyMuPDF is available, renders select pages (title, formula,
  figure, mindmap) to PNG in build/preview/ for visual inspection.

Exit codes: 0 ok, 1 compile error, 2 no TeX engine found.

Usage:
    python scripts/compile_slides.py slides/main.tex [--outdir slides/build]
    python scripts/compile_slides.py slides/main.tex --preview-pages 1,7,10
"""
from __future__ import annotations
import argparse, shutil, subprocess, sys
from pathlib import Path


def find_engine() -> tuple[str, str] | None:
    if shutil.which("latexmk"):
        return "latexmk", "latexmk"
    if shutil.which("xelatex"):
        return "xelatex", "xelatex"
    if shutil.which("pdflatex"):
        return "pdflatex", "pdflatex"
    return None


def compile_tex(engine: str, src: Path, outdir: Path) -> int:
    outdir.mkdir(parents=True, exist_ok=True)
    log = (outdir / "compile.log").open("w", encoding="utf-8", errors="replace")
    try:
        if engine == "latexmk":
            cmd = ["latexmk", "-xelatex", "-interaction=nonstopmode", "-halt-on-error",
                   "-outdir=" + str(outdir), str(src)]
        else:
            cmd = [engine, "-interaction=nonstopmode", "-halt-on-error",
                   "-output-directory=" + str(outdir), str(src)]
        proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
        if proc.returncode == 0 and engine != "latexmk":
            # second pass for cross-references/toc
            proc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
        return proc.returncode
    finally:
        log.close()


def render_previews(pdf: Path, outdir: Path, pages: list[int]) -> list[str]:
    preview = outdir / "preview"
    preview.mkdir(parents=True, exist_ok=True)
    rendered = []
    if shutil.which("pdftoppm"):
        for page in pages:
            out = preview / f"page_{page:03d}"
            subprocess.run(["pdftoppm", "-png", "-r", "96", "-f", str(page),
                            "-l", str(page), str(pdf), str(out)],
                           capture_output=True)
            rendered.append(str(out) + "-1.png")
        return rendered
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf))
        for page in pages:
            if 1 <= page <= doc.page_count:
                pix = doc[page - 1].get_pixmap(dpi=96)
                target = preview / f"page_{page:03d}.png"
                pix.save(str(target))
                rendered.append(str(target))
        doc.close()
        return rendered
    except ImportError:
        return []


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path, help="slides/main.tex")
    p.add_argument("--outdir", type=Path, default=None)
    p.add_argument("--preview-pages", type=str, default="1",
                   help="渲染预览页，逗号分隔，如 1,7,10")
    p.add_argument("--no-preview", action="store_true", help="跳过 PNG 渲染")
    args = p.parse_args()
    src = args.source.resolve()
    if not src.is_file():
        p.error(f"not a file: {src}")
    outdir = (args.outdir or (src.parent / "build")).resolve()
    engine = find_engine()
    if engine is None:
        print("compile error: no latexmk/xelatex/pdflatex found on PATH", file=sys.stderr)
        return 2
    name, binary = engine
    print(f"compiling with {name} ({binary}) -> {outdir}")
    code = compile_tex(binary, src, outdir)
    pdf = outdir / (src.stem + ".pdf")
    if code == 0 and pdf.is_file():
        print(f"OK: {pdf}")
        if not args.no_preview:
            pages = []
            for part in args.preview_pages.split(","):
                part = part.strip()
                if part.isdigit():
                    pages.append(int(part))
            rendered = render_previews(pdf, outdir, pages)
            if rendered:
                print("previews: " + ", ".join(rendered))
            else:
                print("previews skipped: no pdftoppm/PyMuPDF available")
    else:
        print(f"compile failed (exit {code}); see {outdir / 'compile.log'}", file=sys.stderr)
    return 0 if code == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
