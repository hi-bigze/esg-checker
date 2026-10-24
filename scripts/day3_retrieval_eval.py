# -*- coding: utf-8 -*-
"""Day 3: 页级分块 + BGE 检索 + 对照 ground truth 实测召回率
分块策略 v1：一页 = 一个 chunk（规则证据带页码，页级最自然）
"""
import json, re, csv, sys, time
import pymupdf
from sentence_transformers import SentenceTransformer

REPORTS = {
    "changan": "data/reports/changan_2025_esg.pdf",
    "jianghuai": "data/reports/jianghuai_2025_esg.pdf",
}

def load_pages():
    pages = {}  # (report, page_no) -> text
    for rep, path in REPORTS.items():
        doc = pymupdf.open(path)
        for i, p in enumerate(doc):
            t = re.sub(r"\s+", " ", p.get_text()).strip()
            pages[(rep, i + 1)] = t
    return pages

def load_rules():
    import yaml
    with open("rules/ghg_v1.yaml", encoding="utf-8") as f:
        rules = yaml.safe_load(f)
    return {r["id"]: r for r in rules["rules"]}

def load_gt():
    rows = []
    with open("data/annotation/ground_truth_v1.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            r["page"] = int(r["page"]) if r["page"].strip().isdigit() else None
            r["page_alt"] = int(r["page_alt"]) if r["page_alt"].strip().isdigit() else None
            rows.append(r)
    return rows

def main():
    t0 = time.time()
    pages = load_pages()
    print(f"[1] 分块完成：{len(pages)} 页，耗时 {time.time()-t0:.1f}s")

    t1 = time.time()
    model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
    keys = list(pages.keys())
    corpus = [pages[k] if pages[k] else "（本页无文本，可能为图片页）" for k in keys]
    emb = model.encode(corpus, normalize_embeddings=True, show_progress_bar=False)
    print(f"[2] embedding 完成：{emb.shape}，耗时 {time.time()-t1:.1f}s")

    rules = load_rules()
    gt = load_gt()
    # bge 查询需要加指令前缀
    Q = "为这个句子生成表示以用于检索相关文章："
    # v2 查询扩展：规则语言是"准则腔"，报告语言是"报表腔"，加同义词桥接
    EXPAND = {
        "GHG-01": "范围一 温室气体排放总量 直接排放",
        "GHG-02": "范围二 基于位置 外购电力 排放量",
        "GHG-03": "范围二 基于市场 绿电 外购电力",
        "GHG-04": "合并范围 财务合并口径 并表 运营控制权 股权比例",
        "GHG-05": "固定源 移动源 逸散 制程排放 外购热力 能源消耗量",
        "GHG-06": "ISO 14064 GHG Protocol 核算 排放因子 生态环境部 盘查",
        "GHG-07": "基准年 减排目标 降幅 碳中和 目标",
        "GHG-08": "排放强度 万元产值 万元营收 碳排放强度",
        "GHG-09": "范围三 价值链 上游 下游 排放类别",
        "GHG-10": "第三方核查 验证声明 有限保证 SGS 鉴证 GRI 2-5 独立核验",
    }

    results = []
    for row in gt:
        if row["page"] is None:
            continue
        rule = rules[row["rule_id"]]
        qv = model.encode([Q + f"{rule['name']}。{rule.get('requirement','')}"],
                          normalize_embeddings=True)[0]
        qv2 = model.encode([Q + f"{rule['name']}。{EXPAND.get(row['rule_id'],'')}"],
                           normalize_embeddings=True)[0]
        # 只在该报告内检索，v2 取两次查询的逐页最大分
        best = {}
        for i in range(len(keys)):
            if keys[i][0] != row["report"]:
                continue
            best[keys[i][1]] = max(float(qv @ emb[i]), float(qv2 @ emb[i]))
        sims = sorted(((s, (row["report"], p)) for p, s in best.items()), reverse=True)
        top5 = [k[1][1] for k in sims[:5]]
        truth_pages = {row["page"]} | ({row["page_alt"]} if row["page_alt"] else set())
        hit_rank = next((top5.index(p) + 1 for p in top5 if p in truth_pages), None)
        results.append({
            "rule_id": row["rule_id"], "report": row["report"],
            "disclosed": row["disclosed"], "truth": sorted(truth_pages),
            "top5": top5, "hit_rank": hit_rank,
        })

    n = len(results)
    r1 = sum(1 for r in results if r["hit_rank"] == 1)
    r3 = sum(1 for r in results if r["hit_rank"] and r["hit_rank"] <= 3)
    r5 = sum(1 for r in results if r["hit_rank"])
    print(f"\n[3] 召回率（{n} 条有页码的 ground truth）")
    print(f"    recall@1 = {r1}/{n} = {r1/n:.0%}")
    print(f"    recall@3 = {r3}/{n} = {r3/n:.0%}")
    print(f"    recall@5 = {r5}/{n} = {r5/n:.0%}")
    miss = [r for r in results if not r["hit_rank"]]
    for m in miss:
        print(f"    MISS {m['rule_id']} {m['report']} truth={m['truth']} top5={m['top5']}")
    late = [r for r in results if r["hit_rank"] and r["hit_rank"] > 1]
    for m in late:
        print(f"    RANK{m['hit_rank']} {m['rule_id']} {m['report']} truth={m['truth']} top5={m['top5']}")

    import os
    os.makedirs("data/eval", exist_ok=True)
    with open("data/eval/day3_retrieval_results.json", "w", encoding="utf-8") as f:
        json.dump({"summary": {"n": n, "recall@1": r1, "recall@3": r3, "recall@5": r5},
                   "details": results}, f, ensure_ascii=False, indent=1)
    print("\n结果已存 data/eval/day3_retrieval_results.json")
    print(f"总耗时 {time.time()-t0:.1f}s")

if __name__ == "__main__":
    main()
