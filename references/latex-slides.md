# LaTeX Beamer slides 规范

## 推荐页序

1. 标题、出处、复现状态和边界；
2. 研究问题、现象和研究缺口；
3. 贡献与相关工作定位；
4. 符号表和问题定义；
5. 核心假设/定理或因果图；
6. 方法总览；
7. 核心公式（每页只引入一个逻辑跃迁）；
8. 算法伪代码与实现映射；
9. 数据、切分、预处理与实验矩阵；
10. 主结果图/表与逐项对照；
11. 消融、稳健性和失败案例；
12. 差异诊断、限制与结论；
13. 可复现实验清单和写作借鉴；
14. 参考文献与附录公式。

## 公式与代码联动

每个关键公式都要同时显示：公式编号、符号解释、张量/变量形状、代码文件/函数、数值检查。长公式使用 `aligned` 或拆成连续两页；不要把多个未解释的符号塞进一张 slide。算法页标出输入、输出、循环变量、停止条件和复杂度，并在页脚放运行 ID。

图表从核验后的 CSV/JSON/PNG 生成，禁止截图论文后再标注。图注说明数据版本、聚合、误差条、重复次数和复现状态。使用 `\\includegraphics[width=...]` 的相对路径，统一字体、颜色和小数位；表格超宽时拆表或只显示与主张直接相关的列。

## 编译与检查

优先（Unix/macOS）：

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error -outdir=build slides/main.tex
```

跨平台（Windows 也适用，自动探测 latexmk/xelatex/pdflatex）：

```bash
python scripts/compile_slides.py slides/main.tex --preview-pages 1,7,10
```

中文优先使用 `ctexbeamer`；若环境缺少宏包，记录完整错误，不将“编译未通过”包装成成功。必要时改用英文 slides 或安装项目允许的 TeX 依赖，但记录版本。编译后检查 `.log` 中的 `Overfull`、`Undefined`、字体替换和引用警告；用 `compile_slides.py` 的预览或 `pdftoppm` 将首页、公式页、图表页、思维导图页渲染成 PNG 目检（`build/preview/page_*.png`），修复溢出、裁切、字体替换、不可读图例和引用断裂后再交付。

## 可编译起点

复制 `assets/beamer_template.tex`，替换元数据、章节和图片路径。编译产物放在 `slides/build/`，源码与数据放在 `slides/` 下，避免绝对路径和机器私有目录。
