# -*- coding: utf-8 -*-
"""把「记忆评测最小项」表生成 markdown + 可直接打印的 HTML/PDF。

表格内容逐字来自用户给定表格，不做改写；只做排版。
"""
import html
import re
import pathlib
import subprocess

OUT = pathlib.Path(__file__).parent

from memory_eval_items import GROUPS, ROWS

# GROUPS / ROWS 来自 memory_eval_items.py（xlsx / md / 打印版共用同一份数据）。
# ROWS 每行为 (模块序号, 编号, 最小评测项, 交集, 场景, 指标)，模块序号 None 表示沿用上一行。


def md_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", "<br>")


def build_md() -> str:
    lines = [
        "# 记忆评测最小项",
        "",
        "> 11 项 × 6 列：模块 / 编号 / 最小评测项 / 和 AISF 工作交集 / 最小评测场景 / 最小评测指标。",
        "> 「对应原表 3」为与上游评测表的编号锚点。",
        "",
        "| 模块 | 编号 | 最小评测项（原表 3 对应） | 和 AISF 工作交集 | 最小评测场景 | 最小评测指标 |",
        "| --- | :---: | --- | --- | --- | --- |",
    ]
    for gi, num, item, inter, scene, metric in ROWS:
        if gi is not None:
            module = GROUPS[gi][0] + "\n" + GROUPS[gi][1]
        else:
            module = ""
        module = module.replace("<code>", "`").replace("</code>", "`")
        lines.append("| " + " | ".join(
            md_cell(c) for c in (module, num, item, inter, scene, metric)) + " |")
    return "\n".join(lines) + "\n"


def inline(text: str) -> str:
    """转义 + 反引号转 code + 少量符号保护。"""
    text = html.escape(text, quote=False)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", text)


def render_cell(text: str) -> str:
    out = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("•"):
            out.append(f'<p class="li">{inline(line[1:].strip())}</p>')
        elif line.startswith("◦"):
            out.append(f'<p class="sub">{inline(line[1:].strip())}</p>')
        elif re.match(r"^\d+\.\s", line):
            out.append(f'<p class="num">{inline(line)}</p>')
        else:
            out.append(f'<p class="head">{inline(line)}</p>')
    return "".join(out)


def build_html() -> str:
    body_rows = []
    for idx, (gi, num, item, inter, scene, metric) in enumerate(ROWS):
        tds = []
        if gi is not None:
            g = GROUPS[gi]
            # 组首行之后、下一个模块之前的行都是本组成员（其 gi 为 None）
            span = 1
            for nxt in ROWS[idx + 1:]:
                if nxt[0] is not None:
                    break
                span += 1
            tds.append(f'<td class="module g{gi}" rowspan="{span}">'
                       f'<span class="mt">{inline(g[0])}</span><span class="ms">{inline(g[1])}</span></td>')
        tds.append(f'<td class="no">{num}</td>')
        tds.append(f'<td class="item">{render_cell(item)}</td>')
        tds.append(f'<td>{render_cell(inter)}</td>')
        tds.append(f'<td>{render_cell(scene)}</td>')
        tds.append(f'<td>{render_cell(metric)}</td>')
        body_rows.append("      <tr>" + "".join(tds) + "</tr>")

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>记忆评测最小项</title>
<style>
@page {{ size: A4 landscape; margin: 10mm 10mm 12mm; }}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
  color: #1f2328; font-size: 8pt; line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}}
h1 {{ font-size: 13pt; font-weight: 600; margin: 0 0 2mm; letter-spacing: .2px; }}
.meta {{ font-size: 7.5pt; color: #5f6368; margin: 0 0 3mm; }}
.meta span {{ margin-right: 6mm; }}
table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
col.c1 {{ width: 9.2%; }} col.c2 {{ width: 4%; }} col.c3 {{ width: 12.4%; }}
col.c4 {{ width: 15.4%; }} col.c5 {{ width: 33%; }} col.c6 {{ width: 26%; }}
th, td {{ border: .5px solid #b8bcc2; padding: 1.6mm 1.8mm; vertical-align: top; }}
th {{
  background: #eef0f2; font-weight: 600; font-size: 8pt; text-align: left;
  vertical-align: middle; padding: 2mm 1.8mm;
}}
th.c {{ text-align: center; }}
td.module {{ background: #f6f7f8; text-align: center; vertical-align: middle; padding: 2mm .6mm; line-height: 1.35; }}
td.module .mt {{ display: block; font-weight: 600; font-size: 8pt; }}
td.module .ms {{ display: block; color: #5f6368; font-size: 7pt; margin-top: 1mm; }}
td.module code {{ font-size: 6.8pt; }}
td.no {{ text-align: center; font-weight: 600; font-variant-numeric: tabular-nums; white-space: nowrap; }}
td.item .head {{ font-weight: 600; }}
td.item .head + .head {{ font-weight: 400; font-size: 7.2pt; color: #5f6368; }}
p {{ margin: 0 0 1.1mm; }}
p:last-child {{ margin-bottom: 0; }}
.li {{ padding-left: 3.2mm; text-indent: -3.2mm; }}
.li::before {{ content: "•"; display: inline-block; width: 3.2mm; text-indent: 0; }}
.sub {{ padding-left: 7.4mm; text-indent: -3.2mm; color: #3d4148; }}
.sub::before {{ content: "◦"; display: inline-block; width: 3.2mm; text-indent: 0; }}
.num {{ padding-left: 7.4mm; text-indent: -4.6mm; }}
code {{
  font-family: "Cascadia Mono", Consolas, "SFMono-Regular", monospace;
  font-size: 6.9pt; background: #f1f2f4; border-radius: 2px; padding: 0 .6mm;
  white-space: nowrap;
}}
tr {{ page-break-inside: avoid; break-inside: avoid; }}
thead {{ display: table-header-group; }}
.foot {{ margin-top: 3mm; font-size: 7pt; color: #6b7075; display: flex; justify-content: space-between; }}
@media screen {{
  body {{ background: #f2f3f5; padding: 18px; }}
  .sheet {{ background: #fff; max-width: 1180px; margin: 0 auto; padding: 22px 24px 16px; border: 1px solid #dcdfe3; }}
}}
@media print {{ .sheet {{ border: 0; padding: 0; }} body {{ background: #fff; }} }}
</style>
</head>
<body>
<div class="sheet">
  <h1>记忆评测最小项</h1>
  <p class="meta">
    <span>四组 11 项：记忆生命周期 3 · 长期记忆功能 2 · 意图闭环 3 · 端到端效能 3</span>
    <span>编号锚点对应原表 3</span>
    <span>A4 横向 · 可直接打印</span>
  </p>
  <table>
    <colgroup>
      <col class="c1"><col class="c2"><col class="c3"><col class="c4"><col class="c5"><col class="c6">
    </colgroup>
    <thead>
      <tr>
        <th>模块</th>
        <th class="c">编号</th>
        <th>最小评测项<br>（原表 3 对应）</th>
        <th>和 AISF 工作交集</th>
        <th>最小评测场景</th>
        <th>最小评测指标</th>
      </tr>
    </thead>
    <tbody>
{chr(10).join(body_rows)}
    </tbody>
  </table>
  <div class="foot">
    <span>• 为一级条目，◦ 为该条目下的细分指标</span>
    <span>记忆评测最小项</span>
  </div>
</div>
</body>
</html>
"""


if __name__ == "__main__":
    md_path = OUT / "memory_eval_minimal_items.md"
    html_path = OUT / "memory_eval_minimal_items.print.html"
    pdf_path = OUT / "memory_eval_minimal_items.pdf"

    md_path.write_text(build_md(), encoding="utf-8")
    html_path.write_text(build_html(), encoding="utf-8")
    print("md  :", md_path, md_path.stat().st_size)
    print("html:", html_path, html_path.stat().st_size)

    chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
           f"--print-to-pdf={pdf_path}", html_path.as_uri()]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    print("pdf :", pdf_path, pdf_path.stat().st_size if pdf_path.exists() else "FAILED")
    if r.returncode != 0:
        print(r.stderr[-800:])
