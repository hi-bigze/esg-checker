# -*- coding: utf-8 -*-
"""SQLite 数据层：用户 / 核查记录 / 复核动作 / 使用事件 四张表。
选型理由（面试口径）：单机 PoC、无并发、零运维——SQLite 够用且零成本；
生产化时按并发量换 PostgreSQL，代码里只动 get_conn()。
"""
import sqlite3, hashlib, os, json, csv, time

DB_PATH = "data/app.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def hash_pw(pw: str, salt: str) -> str:
    return hashlib.sha256((salt + pw).encode("utf-8")).hexdigest()

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    pw_salt TEXT NOT NULL,
    pw_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'reviewer',   -- 角色：reviewer=复核员 / admin=管理员（看板仅 admin）
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS check_runs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id TEXT NOT NULL,
    rule_name TEXT NOT NULL,
    report TEXT NOT NULL,
    judgment TEXT NOT NULL,          -- 机器判定
    confidence TEXT NOT NULL,
    disposition TEXT NOT NULL,       -- 自动放行/抽查/人工复核
    value TEXT, unit TEXT, page INTEGER, evidence TEXT, reason TEXT,
    match_gt INTEGER,                -- 与人工标注是否一致（0/1）
    batch TEXT NOT NULL,             -- 评测批次标识
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS review_actions(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES check_runs(id),
    username TEXT NOT NULL,
    verdict TEXT NOT NULL,           -- 同意机器判定/需修改/证据不足待定
    comment TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS events(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    action TEXT NOT NULL,            -- login/view_results/submit_review/view_board
    detail TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
"""

def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    # 旧库迁移：users 表若无 role 列则补上（存量账号默认复核员）
    cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
    if "role" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'reviewer'")
    # 种子账号（演示用）：reviewer=复核员，admin=管理员
    if not conn.execute("SELECT 1 FROM users WHERE username='demo'").fetchone():
        salt = os.urandom(8).hex()
        conn.execute("INSERT INTO users(username,pw_salt,pw_hash,role) VALUES(?,?,?,?)",
                     ("demo", salt, hash_pw("demo1234", salt), "reviewer"))
    if not conn.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
        salt = os.urandom(8).hex()
        conn.execute("INSERT INTO users(username,pw_salt,pw_hash,role) VALUES(?,?,?,?)",
                     ("admin", salt, hash_pw("admin1234", salt), "admin"))
    conn.commit()
    conn.close()

def seed_check_runs(batch="day5"):
    """把 Day5 评测结果 + 人工标注导入 check_runs（幂等：同 batch 已导入则跳过）"""
    conn = get_conn()
    if conn.execute("SELECT 1 FROM check_runs WHERE batch=? LIMIT 1", (batch,)).fetchone():
        conn.close(); return 0
    results = json.load(open("data/eval/day5_results.json", encoding="utf-8"))["details"]
    gt = {(r["rule_id"], r["report"]): r for r in
          csv.DictReader(open("data/annotation/ground_truth_v1.csv", encoding="utf-8-sig"))}
    n = 0
    for r in results:
        g = gt.get((r["rule_id"], r["report"]), {})
        conn.execute(
            "INSERT INTO check_runs(rule_id,rule_name,report,judgment,confidence,disposition,"
            "value,unit,page,evidence,reason,match_gt,batch) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r["rule_id"], r["rule_name"], r["report"], r["machine"], r["conf"], r["disposition"],
             r.get("value") or None, r.get("unit") or None,
             int(r["page"]) if str(r.get("page") or "").isdigit() else None,
             r.get("evidence") or None, r.get("reason") or None,
             1 if r["match"] else 0, batch))
        n += 1
    conn.commit(); conn.close()
    return n

def log_event(conn, username, action, detail=""):
    conn.execute("INSERT INTO events(username,action,detail) VALUES(?,?,?)",
                 (username, action, detail))

if __name__ == "__main__":
    t0 = time.time()
    init_db()
    n = seed_check_runs()
    conn = get_conn()
    counts = {t: conn.execute(f"SELECT COUNT(*) c FROM {t}").fetchone()["c"]
              for t in ("users", "check_runs", "review_actions", "events")}
    # 自审：导入数必须等于 20
    assert counts["check_runs"] == 20, f"check_runs {counts['check_runs']} != 20"
    conn.close()
    print("db ready:", counts, f"seeded {n} rows, {time.time()-t0:.1f}s")
