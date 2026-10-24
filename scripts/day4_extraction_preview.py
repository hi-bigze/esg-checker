# -*- coding: utf-8 -*-
"""Day 4 预演：LLM 抽取判定 vs 人工 ground truth 对打
选 4 条：用户预判机器会错的 2 条（GHG-02 changan / GHG-07 jianghuai）+ 2 条对照
"""
import json, re, os, csv
import pymupdf
import yaml
from openai import OpenAI

client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")

REPORTS = {"changan": "data/reports/changan_2025_esg.pdf",
           "jianghuai": "data/reports/jianghuai_2025_esg.pdf"}

# 检索阶段（v2 同款）取 top3 页文本作为证据
from sentence_transformers import SentenceTransformer
EXPAND = {
    "GHG-02": "范围二 基于位置 外购电力 排放量",
    "GHG-03": "范围二 基于市场 绿电 外购电力",
    "GHG-07": "基准年 减排目标 降幅 碳中性 目标",
    "GHG-10": "第三方核查 验证声明 有限保证 SGS 鉴证 GRI 2-5 独立核验",
}

def page_text(rep, pno):
    doc = pymupdf.open(REPORTS[rep])
    return re.sub(r"\s+", " ", doc[pno - 1].get_text()).strip()

# 检索（复用 day3 逻辑，取 top2 页 + GT 页兜底）
def evidence_pages(rule, rep, expand):
    pages = {}
    doc = pymupdf.open(REPORTS[rep])
    for i, p in enumerate(doc):
        pages[i + 1] = re.sub(r"\s+", " ", p.get_text()).strip()
    model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
    Q = "为这个句子生成表示以用于检索相关文章："
    texts = [t if t else "（图片页）" for t in pages.values()]
    emb = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    q1 = model.encode([Q + f"{rule['name']}。{rule.get('requirement','')}"], normalize_embeddings=True)[0]
    q2 = model.encode([Q + f"{rule['name']}。{expand}"], normalize_embeddings=True)[0]
    sims = sorted(((max(float(q1 @ emb[i]), float(q2 @ emb[i])), p) for i, p in enumerate(pages)), reverse=True)
    return [p for _, p in sims[:2]]

CASES = [  # (rule_id, report, gt_page, gt_judgment, note)
    ("GHG-02", "changan", 29, "部分", "用户预判：机器见数字会判'是'，实际未标注口径应为'部分'"),
    ("GHG-07", "jianghuai", 53, "否", "用户预判：机器抓到6.1%会误判，主语是宝钢不是江淮"),
    ("GHG-03", "jianghuai", 93, "是", "对照：应该判对"),
    ("GHG-10", "changan", 133, "否", "对照：GRI索引自标无鉴证，应判'否'"),
]

def judge(rule, ev_texts):
    prompt = f"""你是ESG披露核查员。只依据下面给出的报告原文片段，核查一条披露要求。
要求：{rule['name']} —— {rule.get('requirement','')}
不合格情形：{'; '.join(rule.get('fail_if', []))}

判定规则：
- 是：要求的内容已披露且规范
- 部分：披露了但不完整或未标注关键口径
- 否：完全未披露
- 无法判定：证据不足以判断

输出 JSON：{{"judgment":"是|部分|否|无法判定","evidence":"支撑判定的原文短句","reason":"一句话理由"}}

报告原文片段：
{ev_texts}"""
    r = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}, temperature=0, max_tokens=300)
    return json.loads(r.choices[0].message.content)

def main():
    rules = {r["id"]: r for r in yaml.safe_load(open("rules/ghg_v1.yaml", encoding="utf-8"))["rules"]}
    gt = {(r["rule_id"], r["report"]): r for r in csv.DictReader(open("data/annotation/ground_truth_v1.csv", encoding="utf-8-sig"))}
    out = []
    for rid, rep, gt_page, gt_j, note in CASES:
        rule = rules[rid]
        pages = evidence_pages(rule, rep, EXPAND[rid])
        if gt_page not in pages:
            pages = [gt_page] + pages[:1]  # 检索评估已在 day3 完成，这里固定用 GT 页测抽取
        ev = "\n---\n".join(f"[p{p}] {page_text(rep, p)}" for p in pages[:2])
        res = judge(rule, ev)
        match = "PASS" if res["judgment"] == gt_j else "MISS"
        out.append({"rule": rid, "report": rep, "gt": gt_j, "machine": res["judgment"],
                    "match": match, "reason": res.get("reason", ""), "note": note})
        print(f"{match} {rid} {rep}: 机器={res['judgment']} 人工={gt_j} | {res.get('reason','')[:60]}")
    with open("data/eval/day4_extraction_preview.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    agree = sum(1 for o in out if o["match"] == "PASS")
    print(f"\n一致率 {agree}/{len(out)}")

if __name__ == "__main__":
    main()
