# 思维导图与映射输入

## mindmap JSON

```json
{
  "title": "论文核心问题与主张",
  "branches": [
    {"label": "问题与缺口 [§1]", "children": [
      {"label": "现象 [C01]"}, {"label": "缺口 [C02]"}
    ]},
    {"label": "方法与公式 [§3]", "children": [
      {"label": "目标函数 [Eq. 2]"}, {"label": "算法 [Alg. 1]"}
    ]},
    {"label": "理论/假设", "children": []},
    {"label": "数据与实验", "children": []},
    {"label": "结果与差异", "children": []},
    {"label": "限制与建议", "children": []}
  ]
}
```

节点文字保持短小，使用 `[§x]`、`[Fig. x]`、`[Table y]`、`[run_id]` 回指证据。`make_mindmap.py` 会自动把含 `[](){}#"<>` 等 Mermaid 特殊字符的标签用双引号包裹；若手工编写，请保持同样的引号规则，避免方括号被解析成形状语法。超过一屏时拆成总图和方法/实验子图。

## 代码映射 JSON

```json
[
  {"paper_id":"Eq.2", "paper_location":"p.4", "code":"src/loss.py:18-43",
   "entry":"train.py", "config":["loss.lambda"], "shape":"B×K",
   "test":"tests/test_loss.py", "status":"verified"}
]
```

映射表必须能回答“论文中的哪一项由哪个函数实现、怎样验证、由哪个运行使用”。
