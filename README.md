# paper-reproduction-deconstruction

面向已发表研究论文的系统拆解、代码复现与期刊化写作。接收论文正文、补充材料、附录代码、数据和运行说明，建立证据链与“段落—方法—代码—图表—结果”映射，执行可审计的复现实验，输出拆解报告、思维导图和可编译的 LaTeX Beamer slides。

## 快速开始

```bash
# 1. 材料清单与哈希
python scripts/inventory_project.py <project_root> -o artifacts/inventory.json

# 2. PDF 逐页文本与图表标题
python scripts/extract_pdf.py paper.pdf -o artifacts/pdf/paper.json

# 3. 运行前环境快照
python scripts/snapshot_env.py -o artifacts/env/environment.before.json

# 4. 按 manifest 预览并运行
python scripts/run_manifest.py repro_manifest.json --dry-run
python scripts/run_manifest.py repro_manifest.json -o artifacts/runs

# 5. 数值逐项比较（CSV 按主键对齐）
python scripts/compare_numbers.py paper_table.csv runs/table/metrics.csv \
    --key-column metric --format md -o artifacts/compare/table1.md

# 6. 思维导图、复现清单、slides
python scripts/make_mindmap.py mindmap.json -o artifacts/mindmap.mmd
python scripts/make_repro_checklist.py artifacts/runs/summary.json repro_manifest.json -o artifacts/repro_checklist.md
python scripts/compile_slides.py slides/main.tex --preview-pages 1,7,10
```

## 目录结构

```
paper-reproduction-deconstruction/
├── SKILL.md                      # 主入口：证据基线 → 拆解 → 映射 → 复现 → 核对 → 报告 → slides
├── agents/openai.yaml            # Agent 界面配置
├── assets/beamer_template.tex    # 最小 Beamer 起始模板
├── references/
│   ├── report-schema.md          # 报告结构、复现等级判据、artifacts 目录规范
│   ├── latex-slides.md           # Beamer 结构、公式/图表规范、跨平台编译 QA
│   ├── evidence-and-writing.md   # 证据等级、段落关系、去 AI 味与写作借鉴
│   └── mindmap-and-code-map.md   # mindmap JSON、代码映射 JSON
└── scripts/
    ├── common.py                 # 共享工具（sha256/写 JSON/路径校验）
    ├── inventory_project.py      # 材料清单 + SHA-256（--format md）
    ├── extract_pdf.py            # PDF 逐页文本/图表标题（pdfplumber→pypdf→pdftotext）
    ├── snapshot_env.py           # 运行前后环境快照（OS/GPU/pip freeze）
    ├── run_manifest.py           # 可审计运行（--dry-run/--job/超时/哈希）
    ├── compare_numbers.py        # 逐元素数值比较（--key-column/--format md）
    ├── make_mindmap.py           # JSON → Mermaid mindmap（特殊字符自动转义）
    ├── make_repro_checklist.py   # summary.json → 从零重放清单
    ├── compile_slides.py         # 跨平台编译 + 预览 PNG（Windows 可用）
    └── compile_slides.sh         # Unix 环境备选（保留原脚本）
```

## Windows 说明

所有 Python 脚本在 Windows 上直接可用。TeX 编译请用 `compile_slides.py`（自动探测 latexmk/xelatex/pdflatex）；原 `compile_slides.sh` 仅 Unix 环境可用。PDF 提取若未安装 pdfplumber/pypdf，可安装 `poppler-utils` 后自动回退到 `pdftotext`。

## 复现等级

exact / near / partial / failed 的量化判据见 `references/report-schema.md` §0；等级必须与结果对照表逐项状态一致，无数值核对不得给 exact。
