"""ぽけっと手当（シンプル版）

起動:  python app.py  →  http://127.0.0.1:5000/
"""
import os
import sqlite3
import uuid
from datetime import date, datetime

from flask import Flask, flash, g, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

import gemini

app = Flask(__name__)
app.secret_key = "dev-secret"   # 本番では推測されない文字列に変える

DB_PATH = "pokette.db"

PREFECTURES = ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県", "茨城県", "栃木県", "群馬県",
               "埼玉県", "千葉県", "東京都", "神奈川県", "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県",
               "岐阜県", "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県",
               "鳥取県", "島根県", "岡山県", "広島県", "山口県", "徳島県", "香川県", "愛媛県", "高知県", "福岡県",
               "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"]
# 都道府県コード → 名前（"13" → "東京都"）。"00" は全国
PREF_NAME = {"00": "全国"}
for i, name in enumerate(PREFECTURES, start=1):
    PREF_NAME[f"{i:02d}"] = name


# ------------------------------------------------------------ データベース
def get_db():
    """リクエストごとにDBに接続する（同じリクエスト内では使い回す）"""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row          # row["name"] のように列名で取れるようにする
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(error):
    if "db" in g:
        g.db.close()


def init_db():
    """テーブルを作り、補助金マスタが空ならサンプルを入れる。管理者 admin / admin も作る"""
    db = sqlite3.connect(DB_PATH)
    db.executescript(open("schema.sql", encoding="utf-8").read())
    if db.execute("SELECT COUNT(*) FROM subsidy").fetchone()[0] == 0:
        db.executescript(open("seed.sql", encoding="utf-8").read())
    if db.execute("SELECT COUNT(*) FROM admin_user").fetchone()[0] == 0:
        db.execute("INSERT INTO admin_user (username, password_hash, created_at) VALUES (?, ?, ?)",
                   ("admin", generate_password_hash("admin"), now()))
    db.commit()
    db.close()


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def login_member():
    """ログイン中の会員を返す（ログインしていなければ None）"""
    if "member_id" not in session:
        return None
    return get_db().execute("SELECT * FROM member WHERE id = ?", (session["member_id"],)).fetchone()


# ------------------------------------------------------------ 診断の判定
def match(s, prefecture, children, income, is_single):
    """補助金 s が、入力された条件の人に当てはまるか"""
    if s["deadline"] and s["deadline"] < date.today().isoformat():
        return False                                    # 期限切れ
    if s["target_area"] != "00" and s["target_area"] != prefecture:
        return False                                    # 地域が違う
    if s["single_parent_only"] and not is_single:
        return False                                    # ひとり親限定
    if s["child_required"] and children == 0:
        return False                                    # 子どもが必要
    if s["income_max"] and income != 5 and income > s["income_max"]:
        return False                                    # 年収が上限を超える（5＝わからない は除外しない）
    return True


# ------------------------------------------------------------ SCR-01 HOME
@app.route("/")
def home():
    return render_template("home.html", member=login_member())


# ------------------------------------------------------------ SCR-02 制度診断
@app.route("/diagnosis", methods=["GET", "POST"])
def diagnosis():
    if request.method == "GET":
        return render_template("diagnosis.html", prefectures=PREF_NAME)

    form = request.form
    if not all(form.get(k) for k in ["prefecture", "children_count", "income", "is_single"]):
        flash("すべての質問に答えてください")
        return redirect("/diagnosis")

    prefecture = form["prefecture"]
    children = int(form["children_count"])
    income = int(form["income"])
    is_single = int(form["is_single"])

    db = get_db()
    hits = [s["id"] for s in db.execute("SELECT * FROM subsidy") if match(s, prefecture, children, income, is_single)]

    if "visit_id" not in session:
        session["visit_id"] = str(uuid.uuid4())       # ブラウザごとの訪問ID
    member = login_member()
    cur = db.execute(
        "INSERT INTO diagnosis_log (visit_id, member_id, created_at, prefecture, children_count, income, is_single, subsidy_ids)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (session["visit_id"], member["id"] if member else None, now(),
         prefecture, children, income, is_single, ",".join(str(i) for i in hits)))
    db.commit()
    return redirect(f"/result/{cur.lastrowid}")


# ------------------------------------------------------------ SCR-03 診断結果
@app.route("/result/<int:log_id>")
def result(log_id):
    db = get_db()
    log = db.execute("SELECT * FROM diagnosis_log WHERE id = ?", (log_id,)).fetchone()
    if log is None:
        return redirect("/diagnosis")

    ids = log["subsidy_ids"].split(",") if log["subsidy_ids"] else []
    subsidies = [db.execute("SELECT * FROM subsidy WHERE id = ?", (i,)).fetchone() for i in ids]
    subsidies = [s for s in subsidies if s]                       # 削除された補助金は飛ばす
    subsidies.sort(key=lambda s: s["deadline"] or "9999-99-99")   # 期限が近い順（随時は最後）

    member = login_member()
    favorite_ids = []
    if member:
        favorite_ids = [r["subsidy_id"] for r in db.execute("SELECT subsidy_id FROM favorite WHERE member_id = ?", (member["id"],))]
    return render_template("result.html", log=log, subsidies=subsidies, member=member,
                           favorite_ids=favorite_ids, pref_name=PREF_NAME)


@app.route("/favorite/<int:subsidy_id>", methods=["POST"])
def favorite(subsidy_id):
    """☆保存／解除（ログインした会員だけ）"""
    member = login_member()
    if member is None:
        return redirect("/login")
    db = get_db()
    exists = db.execute("SELECT id FROM favorite WHERE member_id = ? AND subsidy_id = ?", (member["id"], subsidy_id)).fetchone()
    if exists:
        db.execute("DELETE FROM favorite WHERE id = ?", (exists["id"],))
    else:
        db.execute("INSERT INTO favorite (member_id, subsidy_id, created_at) VALUES (?, ?, ?)",
                   (member["id"], subsidy_id, date.today().isoformat()))
    db.commit()
    return redirect(f"/result/{int(request.form['log_id'])}")   # 元の診断結果に戻る


# ------------------------------------------------------------ SCR-04 登録・ログイン
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    email = request.form["email"].strip()
    password = request.form["password"]
    db = get_db()
    if "@" not in email or len(password) < 8:
        flash("メールアドレスと、8文字以上のパスワードを入力してください")
        return redirect("/register")
    if not request.form.get("agree_terms"):
        flash("利用規約に同意してください")
        return redirect("/register")
    if db.execute("SELECT id FROM member WHERE email = ?", (email,)).fetchone():
        flash("このメールアドレスは登録済みです")
        return redirect("/register")

    cur = db.execute("INSERT INTO member (email, password_hash, created_at) VALUES (?, ?, ?)",
                     (email, generate_password_hash(password), now()))
    db.commit()
    session["member_id"] = cur.lastrowid
    return redirect("/mypage")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    member = get_db().execute("SELECT * FROM member WHERE email = ?", (request.form["email"].strip(),)).fetchone()
    if member is None or not check_password_hash(member["password_hash"], request.form["password"]):
        flash("メールアドレスまたはパスワードが違います")
        return redirect("/login")
    session["member_id"] = member["id"]
    return redirect("/mypage")


@app.route("/logout")
def logout():
    session.pop("member_id", None)
    flash("ログアウトしました")
    return redirect("/")


# ------------------------------------------------------------ SCR-05 マイページ
@app.route("/mypage")
def mypage():
    member = login_member()
    if member is None:
        return redirect("/login")
    db = get_db()
    favorites = db.execute(
        "SELECT subsidy.* FROM favorite JOIN subsidy ON subsidy.id = favorite.subsidy_id"
        " WHERE favorite.member_id = ? ORDER BY subsidy.deadline", (member["id"],)).fetchall()
    last = db.execute("SELECT * FROM diagnosis_log WHERE member_id = ? ORDER BY id DESC LIMIT 1", (member["id"],)).fetchone()
    return render_template("mypage.html", member=member, favorites=favorites, last=last, pref_name=PREF_NAME)


@app.route("/withdraw", methods=["POST"])
def withdraw():
    """退会：会員を削除（お気に入りも一緒に消え、診断ログの会員IDは NULL になる）"""
    member = login_member()
    if member:
        get_db().execute("DELETE FROM member WHERE id = ?", (member["id"],))
        get_db().commit()
    session.pop("member_id", None)
    flash("退会が完了しました")
    return redirect("/")


# ------------------------------------------------------------ データセンター（管理者だけ）
TABLES = ["subsidy", "member", "favorite", "diagnosis_log", "admin_user"]


@app.route("/data/login", methods=["GET", "POST"])
def data_login():
    if request.method == "GET":
        return render_template("data_login.html")
    admin = get_db().execute("SELECT * FROM admin_user WHERE username = ?", (request.form["username"],)).fetchone()
    if admin is None or not check_password_hash(admin["password_hash"], request.form["password"]):
        flash("ユーザー名またはパスワードが違います")
        return redirect("/data/login")
    session["admin_id"] = admin["id"]
    return redirect("/data")


@app.route("/data")
def data():
    """テーブルの中身を表示する（?table=member のように切り替える）"""
    if "admin_id" not in session:
        return redirect("/data/login")
    table = request.args.get("table", "subsidy")
    if table not in TABLES:                     # 決めたテーブル名以外はSQLに入れない
        table = "subsidy"
    rows = get_db().execute(f"SELECT * FROM {table}").fetchall()
    columns = rows[0].keys() if rows else []
    return render_template("data.html", tables=TABLES, table=table, rows=rows, columns=columns,
                           prefectures=PREF_NAME, categories=gemini.CATEGORIES,
                           gemini_ready=bool(os.environ.get("GEMINI_API_KEY")))


@app.route("/data/gemini", methods=["POST"])
def data_gemini():
    """Gemini に補助金を聞いて、確認画面に出す（まだ登録しない）"""
    if "admin_id" not in session:
        return redirect("/data/login")
    area = request.form["area"]
    try:
        items = gemini.fetch_subsidies(PREF_NAME[area], request.form["category"])
    except Exception as e:
        flash(f"Gemini から取得できませんでした：{e}")
        return redirect("/data")
    return render_template("data_gemini.html", items=items, area=area)


@app.route("/data/gemini/save", methods=["POST"])
def data_gemini_save():
    """確認画面でチェックした補助金を登録する"""
    if "admin_id" not in session:
        return redirect("/data/login")
    db = get_db()
    checked = request.form.getlist("checked")   # チェックした行の番号
    count = 0
    for n in checked:
        db.execute(
            "INSERT INTO subsidy (name, amount, difficulty, deadline, official_url, category, target_area,"
            " single_parent_only, child_required, income_max, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (request.form[f"name_{n}"], request.form[f"amount_{n}"], request.form[f"difficulty_{n}"],
             request.form[f"deadline_{n}"] or None, request.form[f"official_url_{n}"], request.form[f"category_{n}"],
             request.form["area"], int(request.form[f"single_parent_only_{n}"]), int(request.form[f"child_required_{n}"]),
             request.form[f"income_max_{n}"] or None, now()))
        count += 1
    db.commit()
    flash(f"{count} 件登録しました")
    return redirect("/data?table=subsidy")


@app.route("/data/delete/<int:subsidy_id>", methods=["POST"])
def data_delete(subsidy_id):
    if "admin_id" not in session:
        return redirect("/data/login")
    get_db().execute("DELETE FROM subsidy WHERE id = ?", (subsidy_id,))
    get_db().commit()
    flash(f"補助金ID {subsidy_id} を削除しました")
    return redirect("/data?table=subsidy")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))   # どこから起動しても flask_app フォルダで動かす
    gemini.load_env()
    init_db()
    app.run(debug=True)
