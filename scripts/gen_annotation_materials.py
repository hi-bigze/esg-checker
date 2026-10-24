# -*- coding: utf-8 -*-
"""Day 2 标注素材生成：抽取两份年报 GHG 相关页文本 + 长安 p122 渲染成图 + 生成标注模板"""
import pymupdf, os, re

BASE = r"D:\workbuddy\esg-checker"
OUT = os.path.join(BASE, "data", "annotation")
os.makedirs(OUT, exist_ok=True)

jobs = {
    "changan": (os.path.join(BASE, "data", "reports", "changan_2025_esg.pdf"),
                [21, 28, 29, 30, 31, 32, 33, 34, 122, 133, 136]),
    "jianghuai": (os.path.join(BASE, "data", "reports", "jianghuai_2025_esg.pdf"),
                  [51, 52, 53, 62, 63, 64, 65, 66, 67, 69, 93, 101]),
}

for name, (path, pages) in jobs.items():
    doc = pymupdf.open(path)
    lines = [f"# {name} 标注素材（PDF 页码 = 阅读器显示页码，即第 N 页）"]
    for pno in pages:
        if pno <= doc.page_count:
            t = doc[pno - 1].get_text()
            t = re.sub(r"\n{3,}", "\n\n", t)
            lines.append(f"\n\n===== 第 {pno} 页 =====\n{t}")
    with open(os.path.join(OUT, f"{name}_ghg_pages.txt"), "w", encoding="utf-8") as f:
        f.write("".join(lines))
    print(name, "文本抽取完成")

# 长安 p122 数字乱码，渲染成图片供人工读数
doc = pymupdf.open(jobs["changan"][0])
pix = doc[121].get_pixmap(dpi=200)
pix.save(os.path.join(OUT, "changan_p122_绩效表.png"))
print("changan p122 已渲染为 PNG")

# 标注模板：10 条规则 × 2 份报告 = 20 行
rows = ["rule_id,report,disclosed(是/否/部分),value(原文数值,照抄),unit(原文单位,照抄),page(页码),evidence_quote(原文一句话,照抄),notes"]
rule_ids = [f"GHG-{i:02d}" for i in range(1, 11)]
for rid in rule_ids:
    for rep in ["changan", "jianghuai"]:
        rows.append(f"{rid},{rep},,,,,,")
with open(os.path.join(OUT, "ground_truth_template.csv"), "w", encoding="utf-8-sig") as f:
    f.write("\n".join(rows))
print("标注模板生成：ground_truth_template.csv（20 行）")
