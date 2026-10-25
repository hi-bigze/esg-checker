# -*- coding: utf-8 -*-
"""FastAPI 后端：登录鉴权 + 核查结果 + 复核提交 + 运营看板。
接口契约（面试口径）：JSON over HTTP，cookie 承载 session token，
前端不直接碰数据库——所有数据访问走这层接口。
"""
import secrets
from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app import db

app = FastAPI(title="ESG 披露核查 Agent")
SESSIONS = {}  # token -> username（单机内存 session；多实例部署时换 Redis，接口不变）

class LoginReq(BaseModel):
    username: str
    password: str

class ReviewReq(BaseModel):
    run_id: int
    verdict: str
    comment: str = ""

def require_auth(request: Request) -> str:
    token = request.cookies.get("session")
    if not token or token not in SESSIONS:
        raise HTTPException(401, "未登录或会话过期")
    return SESSIONS[token]

@app.on_event("startup")
def startup():
    db.init_db()
    n = db.seed_check_runs()
    print(f"[startup] db ready, seeded {n} check_runs")

# ---------- 页面 ----------
@app.get("/")
def index():
    return FileResponse("app/static/index.html")

# ---------- 鉴权 ----------
@app.post("/api/login")
def login(req: LoginReq, response: Response):
    conn = db.get_conn()
    u = conn.execute("SELECT * FROM users WHERE username=?", (req.username,)).fetchone()
    conn.close()
    if not u or db.hash_pw(req.password, u["pw_salt"]) != u["pw_hash"]:
        raise HTTPException(401, "用户名或密码错误")
    token = secrets.token_hex(16)
    SESSIONS[token] = req.username
    response.set_cookie("session", token, httponly=True, samesite="lax")
    conn = db.get_conn(); db.log_event(conn, req.username, "login"); conn.commit(); conn.close()
    return {"ok": True, "username": req.username}

@app.post("/api/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get("session")
    SESSIONS.pop(token, None)
    response.delete_cookie("session")
    return {"ok": True}

# ---------- 业务数据 ----------
@app.get("/api/results")
def results(username: str = Depends(require_auth)):
    conn = db.get_conn()
    rows = [dict(r) for r in conn.execute(
        "SELECT cr.*, (SELECT verdict FROM review_actions ra WHERE ra.run_id=cr.id "
        "ORDER BY ra.id DESC LIMIT 1) AS last_review FROM check_runs cr ORDER BY cr.id").fetchall()]
    conn.close()
    return {"results": rows}

@app.post("/api/review")
def review(req: ReviewReq, request: Request, username: str = Depends(require_auth)):
    if req.verdict not in ("同意机器判定", "需修改", "证据不足待定"):
        raise HTTPException(400, "非法复核结论")
    conn = db.get_conn()
    run = conn.execute("SELECT id FROM check_runs WHERE id=?", (req.run_id,)).fetchone()
    if not run:
        conn.close(); raise HTTPException(404, "核查记录不存在")
    conn.execute("INSERT INTO review_actions(run_id,username,verdict,comment) VALUES(?,?,?,?)",
                 (req.run_id, username, req.verdict, req.comment))
    db.log_event(conn, username, "submit_review", f"run={req.run_id} verdict={req.verdict}")
    conn.commit(); conn.close()
    return {"ok": True}

@app.get("/api/board")
def board(username: str = Depends(require_auth)):
    conn = db.get_conn()
    q = lambda sql: conn.execute(sql).fetchone()[0]
    stats = {
        "login_count": q("SELECT COUNT(*) FROM events WHERE action='login'"),
        "review_count": q("SELECT COUNT(*) FROM review_actions"),
        "modify_count": q("SELECT COUNT(*) FROM review_actions WHERE verdict='需修改'"),
        "pending_count": q("SELECT COUNT(*) FROM review_actions WHERE verdict='证据不足待定'"),
        "event_count": q("SELECT COUNT(*) FROM events"),
    }
    stats["modify_rate"] = (f"{stats['modify_count']/stats['review_count']:.0%}"
                            if stats["review_count"] else "—")
    # 高错判规则 Top3（与人工基准不一致次数）——迭代闭环的输入
    top_mismatch = [dict(r) for r in conn.execute(
        "SELECT rule_id, rule_name, SUM(1-match_gt) AS mismatch, COUNT(*) AS total "
        "FROM check_runs GROUP BY rule_id HAVING mismatch>0 "
        "ORDER BY mismatch DESC LIMIT 3").fetchall()]
    conf_dist = [dict(r) for r in conn.execute(
        "SELECT confidence, disposition, COUNT(*) AS n FROM check_runs "
        "GROUP BY confidence, disposition ORDER BY n DESC").fetchall()]
    conn.close()
    return {**stats, "top_mismatch": top_mismatch, "conf_dist": conf_dist}
