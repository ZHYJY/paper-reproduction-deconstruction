#!/usr/bin/env bash
set -euo pipefail
src="${1:?usage: compile_slides.sh slides/main.tex [build-dir]}"
out="${2:-$(dirname "$src")/build}"
mkdir -p "$out"
if command -v latexmk >/dev/null 2>&1; then
  latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir="$out" "$src"
else
  command -v xelatex >/dev/null 2>&1 || { echo "latexmk/xelatex unavailable" >&2; exit 2; }
  xelatex -interaction=nonstopmode -halt-on-error -output-directory="$out" "$src"
  xelatex -interaction=nonstopmode -halt-on-error -output-directory="$out" "$src"
fi
