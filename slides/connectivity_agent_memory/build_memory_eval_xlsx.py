# -*- coding: utf-8 -*-
"""把「记忆评测最小项」表生成为独立 xlsx（纯标准库，无第三方依赖）。

数据源：memory_eval_items.py（与 md / 打印版共用，改一处即全量同步）。

设计要点：
- 第一行即表头，不加标题行，方便整表复制到别处。
- 模块列按组纵向合并，跨行居中。
- 单元格内多行用换行符，wrapText 生效；行高按文本量估算，避免打开后字被压扁。
- 打印默认 A4 横向、缩放到 1 页宽。
"""
import math
import os
import zipfile
from xml.sax.saxutils import escape

from memory_eval_items import HEADERS, GROUPS, resolved_rows

OUT = "memory_eval_minimal_items.xlsx"

ROWS = resolved_rows()          # (gi, num, item, inter, scene, metric)
COL_W = [16, 6, 22, 34, 52, 30]
FONT_NAME = "等线"


def cell_text(gi: int, row) -> list:
    """拼一行 6 个单元格的纯文本；xlsx 里不需要 markdown 反引号。"""
    gi_, num, item, inter, scene, metric = row
    module = (GROUPS[gi][0] + "\n" + GROUPS[gi][1]).replace("`", "")
    vals = [module, num, item, inter, scene, metric]
    return [v.replace("`", "") for v in vals]


def disp_width(s: str) -> int:
    """粗略显示宽度：CJK 记 2，其余记 1。"""
    return sum(2 if ord(ch) > 0x2E7F else 1 for ch in s)


def est_lines(text: str, width_chars: float) -> int:
    limit = max(8.0, width_chars - 1.2)
    n = 0
    for seg in text.split("\n"):
        n += max(1, math.ceil(disp_width(seg) / limit))
    return n


def row_height(cells) -> float:
    lines = max(est_lines(v, COL_W[i]) for i, v in enumerate(cells))
    return round(min(409, lines * 15.6 + 7), 1)


def col_letter(idx: int) -> str:
    s, i = "", idx + 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def cell(ref: str, style: int, text: str) -> str:
    t = escape(text).replace("\n", "&#10;")
    return (f'<c r="{ref}" s="{style}" t="inlineStr">'
            f'<is><t xml:space="preserve">{t}</t></is></c>')


def build_sheet() -> str:
    data = [cell_text(gi, row) for gi, row in zip([r[0] for r in ROWS], ROWS)]
    n_rows = len(data) + 1

    out = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
           '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
           '<sheetPr><pageSetUpPr fitToPage="1"/></sheetPr>',
           f'<dimension ref="A1:{col_letter(len(HEADERS)-1)}{n_rows}"/>',
           '<sheetViews><sheetView tabSelected="1" workbookViewId="0">',
           '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>',
           '<selection pane="bottomLeft" activeCell="A2" sqref="A2"/>',
           '</sheetView></sheetViews>',
           '<sheetFormatPr defaultRowHeight="15" defaultColWidth="9"/>',
           '<cols>']
    for i, w in enumerate(COL_W):
        out.append(f'<col min="{i+1}" max="{i+1}" width="{w}" customWidth="1"/>')
    out.append('</cols><sheetData>')

    # 表头
    out.append('<row r="1" ht="34" customHeight="1">')
    for i, h in enumerate(HEADERS):
        out.append(cell(f"{col_letter(i)}1", 1, h))
    out.append('</row>')

    # 数据行：A 列按组只写首行（其余行由 mergeCell 覆盖），写入重复值也无害
    for r, cells in enumerate(data, start=2):
        h = row_height(cells)
        out.append(f'<row r="{r}" ht="{h}" customHeight="1">')
        for i, v in enumerate(cells):
            style = 4 if i == 1 else (3 if i == 0 else 2)
            out.append(cell(f"{col_letter(i)}{r}", style, v))
        out.append('</row>')
    out.append('</sheetData>')

    # 模块列合并：按连续相同的 gi 归组
    gis = [row[0] for row in ROWS]
    groups, s = [], 0
    for i in range(1, len(gis) + 1):
        if i == len(gis) or gis[i] != gis[s]:
            groups.append((s, i - 1))
            s = i
    merges = [f"A{a + 2}:A{b + 2}" for a, b in groups if b > a]
    if merges:
        out.append(f'<mergeCells count="{len(merges)}">')
        out += [f'<mergeCell ref="{m}"/>' for m in merges]
        out.append('</mergeCells>')

    out.append('<pageMargins left="0.35" right="0.35" top="0.5" bottom="0.5" '
               'header="0.2" footer="0.2"/>')
    out.append('<pageSetup paperSize="9" orientation="landscape" '
               'fitToWidth="1" fitToHeight="0" horizontalDpi="600" verticalDpi="600"/>')
    out.append('</worksheet>')
    return "".join(out)


STYLES = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="5">
<font><sz val="11"/><color rgb="FF1F2937"/><name val="{FONT_NAME}"/><charset val="134"/></font>
<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="{FONT_NAME}"/><charset val="134"/></font>
<font><sz val="11"/><color rgb="FF1F2937"/><name val="{FONT_NAME}"/><charset val="134"/></font>
<font><b/><sz val="11"/><color rgb="FF111827"/><name val="{FONT_NAME}"/><charset val="134"/></font>
<font><b/><sz val="12"/><color rgb="FF0F172A"/><name val="{FONT_NAME}"/><charset val="134"/></font>
</fonts>
<fills count="4">
<fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF1F2937"/><bgColor indexed="64"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFF3F4F6"/><bgColor indexed="64"/></patternFill></fill>
</fills>
<borders count="2">
<border><left/><right/><top/><bottom/><diagonal/></border>
<border><left style="thin"><color rgb="FFD1D5DB"/></left><right style="thin"><color rgb="FFD1D5DB"/></right><top style="thin"><color rgb="FFD1D5DB"/></top><bottom style="thin"><color rgb="FFD1D5DB"/></bottom><diagonal/></border>
</borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="5">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
<xf numFmtId="0" fontId="2" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="left" vertical="top" wrapText="1"/></xf>
<xf numFmtId="0" fontId="3" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
<xf numFmtId="0" fontId="4" fillId="0" borderId="1" xfId="0" applyFont="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
</cellXfs>
<cellStyles count="1"><cellStyle name="常规" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''

CONTENT_TYPES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>'''

RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>'''

WORKBOOK = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="最小评测项" sheetId="1" r:id="rId1"/></sheets>
</workbook>'''

WB_RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, OUT)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("xl/workbook.xml", WORKBOOK)
        z.writestr("xl/_rels/workbook.xml.rels", WB_RELS)
        z.writestr("xl/styles.xml", STYLES)
        z.writestr("xl/worksheets/sheet1.xml", build_sheet())
    print("wrote", path, os.path.getsize(path), "bytes")


if __name__ == "__main__":
    main()
