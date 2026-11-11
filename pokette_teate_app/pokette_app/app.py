from flask import Flask, render_template, request, jsonify
import sqlite3, os, uuid
from datetime import date, datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "pokette.db")
app = Flask(__name__)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if os.path.exists(DB_PATH):
        return
    conn = get_db()
    with open(os.path.join(BASE_DIR, "schema.sql"), encoding="utf-8") as f:
        conn.executescript(f.read())
    seed = [
        ("児童手当", "月額1万円～", "easy", None, "子育て", "00", 0, 1, None, "https://www.cfa.go.jp/policies/kokoseido/jidouteate/"),
        ("ひとり親家庭等医療費助成", "医療費の自己負担を助成", "normal", None, "ひとり親支援", "00", 1, 1, None, "https://www.cfa.go.jp/"),
        ("子育て世帯への住宅支援", "家賃・住宅費を支援", "normal", None, "住まい", "00", 0, 1, 3, "https://www.mlit.go.jp/"),
        ("教育費支援制度", "学用品・教育費を支援", "easy", None, "教育", "00", 0, 1, 3, "https://www.mext.go.jp/"),
        ("就学支援金", "授業料を支援", "normal", None, "教育", "00", 0, 1, 4, "https://www.mext.go.jp/"),
        ("地域子育て応援給付", "年額5万円程度", "easy", None, "子育て", "27", 0, 1, 4, "https://www.cfa.go.jp/"),
        ("ひとり親就業支援", "受講費・就業費を支援", "hard", None, "仕事", "00", 1, 1, 4, "https://www.cfa.go.jp/"),
        ("住宅リフォーム支援", "工事費を一部助成", "hard", None, "住まい", "27", 0, 0, 3, "https://www.mlit.go.jp/"),
    ]
    conn.executemany("""
        INSERT INTO subsidy(name,amount,difficulty,deadline,category,target_area,
        single_parent_only,child_required,income_max,official_url)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, seed)
    conn.commit()
    conn.close()

@app.route("/")
def index():
    return render_template("diagnosis.html")

@app.route("/result")
def result():
    return render_template("result.html")

@app.post("/api/diagnose")
def diagnose():
    data = request.get_json(force=True)
    prefecture = str(data.get("prefecture",""))
    children = int(data.get("children",0))
    income = int(data.get("income",5))
    is_single = bool(data.get("singleParent",False))

    conn = get_db()
    rows = conn.execute("SELECT * FROM subsidy ORDER BY id").fetchall()
    conn.close()

    today = date.today()
    results = []
    for r in rows:
        if r["deadline"]:
            try:
                if date.fromisoformat(r["deadline"]) < today:
                    continue
            except ValueError:
                pass
        if r["target_area"] not in ("00", prefecture):
            continue
        if r["single_parent_only"] and not is_single:
            continue
        if r["child_required"] and children < 1:
            continue
        if r["income_max"] is not None and income != 5 and income > r["income_max"]:
            continue
        results.append(dict(r))

    return jsonify({
        "count": len(results),
        "conditions": {
            "prefecture": prefecture, "children": children,
            "income": income, "singleParent": is_single
        },
        "subsidies": results
    })

@app.get("/api/subsidies")
def subsidies():
    conn = get_db()
    rows = conn.execute("SELECT * FROM subsidy ORDER BY id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
