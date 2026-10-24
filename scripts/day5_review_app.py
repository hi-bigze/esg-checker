# -*- coding: utf-8 -*-
"""Day 5: Gradio 人工复核界面。
加载 day5_results.json，展示核查表 + 页码证据，支持对「抽查/人工复核」条目标记复核结论。
复核结论落盘 data/review/review_status.json（键: rule_id|report）。
启动: .\\venv\\Scripts\\python.exe scripts\\day5_review_app.py  然后浏览器开 http://127.0.0.1:7860
"""
import os, json, time
import gradio as gr

DATA = "data/eval/day5_results.json"
REVIEW = "data/review/review_status.json"

d = json.load(open(DATA, encoding="utf-8"))
details = d["details"]
os.makedirs("data/review", exist_ok=True)
reviews = json.load(open(REVIEW, encoding="utf-8")) if os.path.exists(REVIEW) else {}

def overview_table():
    rows = []
    for r in details:
        k = f"{r['rule_id']}|{r['report']}"
        rev = reviews.get(k, {})
        rows.append([r["rule_id"], r["report"], r["machine"], r["conf"],
                     r["disposition"], rev.get("verdict", "未复核"), rev.get("comment", "")])
    return rows

def queue_items():
    return [f"{r['rule_id']} | {r['report']} | 机器={r['machine']}({r['conf']})"
            for r in details if r["disposition"] in ("抽查", "人工复核")]

def load_detail(sel):
    if not sel:
        return "", "", "", gr.update(value=None)
    rid, rest = sel.split(" | ", 1)
    rep = rest.split(" | ")[0]
    r = next(x for x in details if x["rule_id"] == rid and x["report"] == rep)
    ev = f"规则: {r['rule_name']}\n机器判定: {r['machine']}（置信度 {r['conf']}，处置: {r['disposition']}）"
    ev += f"\n披露值: {r['value'] or '—'} {r['unit'] or ''}    证据页: {r.get('evidence_pages')}"
    ev += f"\n机器理由: {r['reason']}"
    return ev, f"报告: {rep}", r["evidence_pages"], gr.update(value=None)

def save(sel, verdict, comment):
    if not sel or not verdict:
        return "请先选择条目并给出复核结论", overview_table()
    rid, rest = sel.split(" | ", 1)
    rep = rest.split(" | ")[0]
    reviews[f"{rid}|{rep}"] = {"verdict": verdict, "comment": comment,
                                "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
    json.dump(reviews, open(REVIEW, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return f"已保存: {rid} {rep} -> {verdict}", overview_table()

with gr.Blocks(title="ESG 披露核查 · 人工复核台") as demo:
    gr.Markdown("## ESG 温室气体披露核查 · 人工复核台\n机器初筛结论 + 页码证据 → 人工复核 → 复核结论落盘。"
                "原则：机器结论不替代人工与审计意见。")
    with gr.Tab("核查总表"):
        tbl = gr.Dataframe(value=overview_table(), headers=["规则", "报告", "机器判定", "置信度", "处置", "复核结论", "复核备注"],
                           interactive=False, wrap=True)
        refresh = gr.Button("刷新总表")
        refresh.click(overview_table, outputs=tbl)
    with gr.Tab("复核工作台"):
        q = gr.Dropdown(choices=queue_items(), label="选择待复核条目（抽查/人工复核）")
        detail = gr.Textbox(label="机器判定详情", lines=5)
        pages_box = gr.Textbox(label="证据页码（对照报告原文核对）")
        verdict = gr.Radio(["同意机器判定", "需修改（备注说明）", "证据不足待定"], label="复核结论")
        comment = gr.Textbox(label="复核备注", lines=2)
        save_btn = gr.Button("保存复核结论")
        status = gr.Textbox(label="状态", interactive=False)
        q.change(load_detail, inputs=q, outputs=[detail, pages_box, pages_box, verdict])
        save_btn.click(save, inputs=[q, verdict, comment], outputs=[status, tbl])

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=False, quiet=True)
