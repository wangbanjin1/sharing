# -*- coding: utf-8 -*-
# 从报告 4.4 节抽取因子表 -> two_layer_factors.csv -> two_layer_factors.xlsx
# 报告表格改动后重跑本脚本即可同步两个产物。

import io, re, html, csv

SRC = 'storyline_and_evaluation_merged_technical_route_report.html'
s = io.open(SRC, encoding='utf-8').read()

i = s.find('<div class="table-wrap">', s.find('id="sec-4-4"'))
j = s.find('</table>', i) + len('</table>')
blk = s[i:j]

tbody = re.search(r'<tbody>(.*?)</tbody>', blk, flags=re.S).group(1)
rows = re.findall(r'<tr[^>]*>.*?</tr>', tbody, flags=re.S)
assert len(rows) == 40, len(rows)

# ---------- CSV：展开 rowspan ----------
def cells(r):
    out = []
    for m in re.finditer(r'<td([^>]*)>(.*?)</td>', r, flags=re.S):
        attr, inner = m.group(1), m.group(2)
        rs = re.search(r'rowspan="(\d+)"', attr)
        txt = re.sub(r'<br\s*/?>', ' ', inner)
        txt = re.sub(r'<[^>]+>', '', txt)
        txt = html.unescape(txt)
        txt = re.sub(r'\s+', ' ', txt).strip()
        out.append((int(rs.group(1)) if rs else 1, txt))
    return out

flat = []
carry = {}
for r in rows:
    cs = cells(r)
    if cs[0][0] > 1:
        group = cs[0][1]
        carry['group'] = group
        carry['left'] = cs[0][0]
        rest = cs[1:]
        flat.append([group] + [t for _, t in rest])
        carry['left'] -= 1
    else:
        flat.append([carry['group']] + [t for _, t in cs])
        carry['left'] -= 1
        if carry['left'] == 0:
            carry.pop('group', None)

assert len(flat) == 40
assert all(len(x) == 6 for x in flat), [len(x) for x in flat]

# 两层各自从“一”起编号，合并成一张表会重名 → 分组名加层前缀，便于筛选
flat = [[('L1·' if r[1].startswith('L1-') else 'L2·') + r[0]] + r[1:] for r in flat]

with io.open('two_layer_factors.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['分组', '层·编号', '因子', '粒度', '取值域（枚举 / 区间 / 组合）', '依赖与约束'])
    w.writerows(flat)


# ============ 以下：CSV -> XLSX ============
import io, csv, math
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

rows = list(csv.reader(io.open('two_layer_factors.csv', encoding='utf-8-sig')))
header, data = rows[0], rows[1:]
assert len(data) == 40 and all(len(r) == 6 for r in data)

INK = '1A1A1A'
ACCENT = '24456E'
FAINT = 'E6E6E6'
BAND = 'FAFAF7'

thin = Side(style='thin', color=FAINT)
border = Border(left=thin, right=thin, top=thin, bottom=thin)

head_font = Font(name='微软雅黑', size=10, bold=True, color='FFFFFF')
head_fill = PatternFill('solid', fgColor=ACCENT)
body_font = Font(name='微软雅黑', size=10, color=INK)
mono_font = Font(name='Consolas', size=10, color=ACCENT)

WIDTHS = [19, 11.5, 16, 7.5, 64, 34]


def disp_len(t):
    return sum(2 if ord(c) > 127 else 1 for c in str(t))


def fit_height(values):
    lines = 1
    for v, w in zip(values, WIDTHS):
        lines = max(lines, math.ceil(disp_len(v) / (w * 1.05)))
    return max(21, lines * 14.6 + 5)


wb = Workbook()

# ---------------- Sheet 1：说明 ----------------
ws = wb.active
ws.title = '说明'
ws.sheet_view.showGridLines = False
ws.column_dimensions['A'].width = 14
ws.column_dimensions['B'].width = 96

ws['A1'] = '两层因子取值总表'
ws['A1'].font = Font(name='微软雅黑', size=16, bold=True, color=INK)
ws.merge_cells('A1:B1')
ws.row_dimensions[1].height = 30

ws['A2'] = '故事线生成器 · 因子字典（40 个因子：排布层 L1 13 个，内容层 L2 27 个）'
ws['A2'].font = Font(name='微软雅黑', size=10, color='6B6B6B')
ws.merge_cells('A2:B2')
ws.row_dimensions[2].height = 20

NOTES = [
    ('记法', '{a / b / c} 枚举取一；[a, b] 区间内连续采样；a:b 比例；× 各维独立采样后组合；⊆ 可多选子集；∅ 不采样（保持缺失，交由 L2-14 判定为“当前未知”）。'),
    ('粒度', '全局：整条故事线取一次；用户：每个 persona 取一次（允许跨期变化）；线：每条业务任务线取一次；节点：每个事件节点独立取。'),
    ('依赖', '←L1-n / ←L2-n 表示父因子为排布层 / 内容层第 n 号；“仅当……”是硬条件——父条件不满足时不采样，也不填默认值。'),
    ('〔建议〕', '按当前样本量推的工程默认值，用于统一口径，不是论文结论。'),
    ('编号', 'L1 = 排布层（时间范围与规模、主支线结构与变化趋势、测试点与覆盖），L2 = 内容层（用户身份、偏好、异常、交互）。'),
    ('来源', '与《故事线与评测技术路线报告》表 4.3 一致；本文件为独立机读版，分组列已展开，每行一条因子。'),
]
r = 4
for k, v in NOTES:
    ws.cell(r, 1, k).font = Font(name='微软雅黑', size=10, bold=True, color=ACCENT)
    ws.cell(r, 1).alignment = Alignment(vertical='top')
    c = ws.cell(r, 2, v)
    c.font = Font(name='微软雅黑', size=10, color=INK)
    c.alignment = Alignment(wrap_text=True, vertical='top')
    ws.row_dimensions[r].height = max(20, math.ceil(disp_len(v) / 100) * 15 + 6)
    r += 1

ws.cell(r + 1, 1, '工作表').font = Font(name='微软雅黑', size=10, bold=True, color=ACCENT)
ws.cell(r + 2, 1, '因子总表').font = body_font
ws.cell(r + 2, 2, '分组合并、配色分块，适合阅读与打印（横向 A4，表头跨页重复）').font = body_font
ws.cell(r + 3, 1, '机读版').font = body_font
ws.cell(r + 3, 2, '一行一条、不合并，首行冻结并启用筛选，便于排序、diff 与导入生成器').font = body_font

# ---------------- Sheet 2：因子总表（合并分组） ----------------
ws2 = wb.create_sheet('因子总表')
ws2.sheet_view.showGridLines = False
for i, w in enumerate(WIDTHS, 1):
    ws2.column_dimensions[get_column_letter(i)].width = w

for i, h in enumerate(header, 1):
    c = ws2.cell(1, i, h)
    c.font = head_font
    c.fill = head_fill
    c.alignment = Alignment(horizontal='left' if i in (1, 3, 5, 6) else 'center',
                            vertical='center', wrap_text=True)
    c.border = border
ws2.row_dimensions[1].height = 26

# 分组切块
groups = []
for row in data:
    if not groups or groups[-1][0] != row[0]:
        groups.append([row[0], 1])
    else:
        groups[-1][1] += 1

start = 2
for gname, cnt in groups:
    for k in range(cnt):
        idx = start + k
        row = data[start - 2 + k]
        for j, v in enumerate(row, 1):
            c = ws2.cell(idx, j, v)
            c.border = border
            c.alignment = Alignment(wrap_text=True, vertical='top',
                                    horizontal='center' if j == 4 else 'left')
            if j == 1:
                c.font = Font(name='微软雅黑', size=10, bold=True, color=INK)
                c.fill = PatternFill('solid', fgColor=BAND)
                c.alignment = Alignment(wrap_text=True, vertical='top', horizontal='left')
            elif j == 2:
                c.font = mono_font
                c.alignment = Alignment(wrap_text=False, vertical='top', horizontal='center')
            elif j == 3:
                c.font = Font(name='微软雅黑', size=10, bold=True, color=INK)
            elif j == 4:
                c.font = Font(name='微软雅黑', size=9, color='7A7A7A')
            else:
                c.font = body_font
        ws2.row_dimensions[idx].height = fit_height(row)
    if cnt > 1:
        ws2.merge_cells(start_row=start, start_column=1, end_row=start + cnt - 1, end_column=1)
        ws2.cell(start, 1).alignment = Alignment(wrap_text=True, vertical='top', horizontal='left')
    # 组间上边线
    for j in range(1, 7):
        cc = ws2.cell(start, j)
        cc.border = Border(left=thin, right=thin, bottom=thin,
                           top=Side(style='medium', color='C9C9C9'))
    start += cnt

ws2.freeze_panes = 'A2'
ws2.print_title_rows = '1:1'
ws2.page_setup.orientation = 'landscape'
ws2.page_setup.paperSize = ws2.PAPERSIZE_A4
ws2.page_setup.fitToWidth = 1
ws2.page_setup.fitToHeight = 0
ws2.sheet_properties.pageSetUpPr.fitToPage = True
ws2.print_options.horizontalCentered = True

# ---------------- Sheet 3：机读版 ----------------
ws3 = wb.create_sheet('机读版')
for i, w in enumerate(WIDTHS, 1):
    ws3.column_dimensions[get_column_letter(i)].width = w
for i, h in enumerate(header, 1):
    c = ws3.cell(1, i, h)
    c.font = head_font
    c.fill = head_fill
    c.alignment = Alignment(vertical='center', wrap_text=True)
ws3.row_dimensions[1].height = 24
for ridx, row in enumerate(data, 2):
    for j, v in enumerate(row, 1):
        c = ws3.cell(ridx, j, v)
        c.font = mono_font if j == 2 else body_font
        c.alignment = Alignment(wrap_text=True, vertical='top',
                                horizontal='center' if j in (2, 4) else 'left')
    ws3.row_dimensions[ridx].height = fit_height(row)

ws3.freeze_panes = 'A2'
last = len(data) + 1
ref = 'A1:F%d' % last
tab = Table(displayName='FactorDict', ref=ref)
tab.tableStyleInfo = TableStyleInfo(name='TableStyleLight1', showRowStripes=True)
ws3.add_table(tab)
ws3.auto_filter.ref = ref

wb.save('two_layer_factors.xlsx')
print('saved xlsx:', len(data), 'rows,', len(groups), 'groups')
