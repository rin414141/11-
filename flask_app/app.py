"""ぽけっと手当（シンプル版）

起動:  python app.py  →  http://127.0.0.1:5000/
"""
import os
import re
import sqlite3
import uuid
from datetime import date, datetime, timedelta
from urllib.parse import urlparse

from flask import Flask, abort, flash, g, redirect, render_template, request, session
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


def ensure_visit_id():
    if "visit_id" not in session:
        session["visit_id"] = str(uuid.uuid4())
    return session["visit_id"]


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

    visit_id = ensure_visit_id()
    member = login_member()
    cur = db.execute(
        "INSERT INTO diagnosis_log (visit_id, member_id, created_at, prefecture, children_count, income, is_single, subsidy_ids)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (visit_id, member["id"] if member else None, now(),
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


@app.route("/out/<int:subsidy_id>")
def official_click(subsidy_id):
    db = get_db()
    subsidy = db.execute("SELECT id, official_url FROM subsidy WHERE id = ?", (subsidy_id,)).fetchone()
    if subsidy is None:
        abort(404)
    target = urlparse(subsidy["official_url"])
    if target.scheme != "https" or not target.netloc:
        abort(400)

    member = login_member()
    db.execute(
        "INSERT INTO official_click (visit_id, member_id, subsidy_id, created_at) VALUES (?, ?, ?, ?)",
        (ensure_visit_id(), member["id"] if member else None, subsidy_id, now()))
    db.commit()
    return redirect(subsidy["official_url"])


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
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or not re.fullmatch(
        r"(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,32}", password
    ):
        flash("有効なメールアドレスと、英字・数字を含む8〜32文字のパスワードを入力してください")
        return redirect("/register")
    if not request.form.get("agree_terms"):
        flash("利用規約に同意してください")
        return redirect("/register")
    if db.execute("SELECT id FROM member WHERE email = ?", (email,)).fetchone():
        flash("このメールアドレスは登録済みです")
        return redirect("/register")

    cur = db.execute(
        "INSERT INTO member (email, password_hash, notify_deadline, agree_partner, created_at) VALUES (?, ?, ?, ?, ?)",
        (email, generate_password_hash(password), int(bool(request.form.get("notify_deadline"))),
         int(bool(request.form.get("agree_partner"))), now()))
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
        " WHERE favorite.member_id = ? ORDER BY subsidy.deadline IS NULL, subsidy.deadline",
        (member["id"],)).fetchall()
    last = db.execute("SELECT * FROM diagnosis_log WHERE member_id = ? ORDER BY id DESC LIMIT 1", (member["id"],)).fetchone()
    today = date.today().isoformat()
    week_end = (date.today() + timedelta(days=7)).isoformat()
    soon_count = sum(1 for item in favorites if item["deadline"] and today <= item["deadline"] <= week_end)
    return render_template("mypage.html", member=member, favorites=favorites, last=last,
                           pref_name=PREF_NAME, today=today, week_end=week_end, soon_count=soon_count,
                           child_labels={0: "0人", 1: "1人", 2: "2人", 3: "3人", 4: "4人以上"},
                           income_labels={1: "300万円未満", 2: "300〜500万円", 3: "500〜800万円",
                                          4: "800万円以上", 5: "わからない"})


@app.route("/mypage/settings", methods=["POST"])
def mypage_settings():
    member = login_member()
    if member is None:
        return redirect("/login")
    db = get_db()
    db.execute(
        "UPDATE member SET notify_deadline = ?, agree_partner = ? WHERE id = ?",
        (int(request.form.get("notify_deadline") == "1"),
         int(request.form.get("agree_partner") == "1"), member["id"]))
    db.commit()
    flash("お知らせ設定を保存しました")
    return redirect("/mypage")


@app.route("/account", methods=["GET", "POST"])
def account():
    member = login_member()
    if member is None:
        return redirect("/login")
    if request.method == "GET":
        return render_template("account.html", member=member)

    email = request.form.get("email", "").strip()
    new_password = request.form.get("new_password", "")
    current_password = request.form.get("current_password", "")
    if not current_password or not check_password_hash(member["password_hash"], current_password):
        flash("現在のパスワードが正しくありません")
        return redirect("/account")
    if not email and not new_password:
        flash("変更する項目を入力してください")
        return redirect("/account")
    if email and (len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email)):
        flash("メールアドレスの形式が正しくありません")
        return redirect("/account")
    db = get_db()
    if email and db.execute(
        "SELECT id FROM member WHERE email = ? AND id != ?", (email, member["id"])
    ).fetchone():
        flash("このメールアドレスは登録済みです")
        return redirect("/account")
    if new_password and (
        not 8 <= len(new_password) <= 32
        or not re.fullmatch(r"(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]+", new_password)
    ):
        flash("新しいパスワードは半角英数字8〜32文字で、英字と数字を各1文字以上入れてください")
        return redirect("/account")

    updates = []
    values = []
    if email:
        updates.append("email = ?")
        values.append(email)
    if new_password:
        updates.append("password_hash = ?")
        values.append(generate_password_hash(new_password))
    values.append(member["id"])
    db.execute(f"UPDATE member SET {', '.join(updates)} WHERE id = ?", values)
    db.commit()
    flash("アカウント情報を変更しました")
    return redirect("/mypage")


@app.route("/withdraw", methods=["POST"])
def withdraw():
    """退会：会員を削除（お気に入りも一緒に消え、診断ログの会員IDは NULL になる）"""
    member = login_member()
    db = get_db()
    reason = request.form.get("reason", "")
    if reason in {"もう必要なくなった", "欲しい制度が見つからなかった", "使い方がわかりにくかった", "その他"}:
        db.execute("INSERT INTO withdrawal_feedback (reason, created_at) VALUES (?, ?)", (reason, now()))
    if member:
        db.execute("DELETE FROM member WHERE id = ?", (member["id"],))
    db.commit()
    session.pop("member_id", None)
    flash("退会が完了しました")
    return redirect("/")


# ------------------------------------------------------------ データセンター（管理者だけ）
TABLES = ["subsidy", "member", "favorite", "diagnosis_log", "admin_user",
          "withdrawal_feedback", "official_click"]


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
    db = get_db()
    labels = {"easy": "簡単", "normal": "ふつう", "hard": "難しい"}
    counts = {
        row["difficulty"]: row
        for row in db.execute(
            "SELECT subsidy.difficulty, COUNT(official_click.id) AS clicks,"
            " COUNT(DISTINCT official_click.visit_id) AS users"
            " FROM subsidy LEFT JOIN official_click ON official_click.subsidy_id = subsidy.id"
            " GROUP BY subsidy.difficulty"
        )
    }
    difficulty_stats = [
        {"difficulty": key, "label": labels[key],
         "clicks": counts[key]["clicks"] if key in counts else 0,
         "users": counts[key]["users"] if key in counts else 0}
        for key in ("easy", "normal", "hard")
    ]
    max_clicks = max((item["clicks"] for item in difficulty_stats), default=0)
    for item in difficulty_stats:
        item["bar_width"] = round(item["clicks"] * 100 / max_clicks) if max_clicks else 0
    subsidy_usage = db.execute(
        "SELECT subsidy.id, subsidy.name, subsidy.difficulty, COUNT(official_click.id) AS clicks,"
        " COUNT(DISTINCT official_click.visit_id) AS users"
        " FROM subsidy LEFT JOIN official_click ON official_click.subsidy_id = subsidy.id"
        " GROUP BY subsidy.id ORDER BY clicks DESC, subsidy.name"
    ).fetchall()
    metrics = {
        "registered_users": db.execute("SELECT COUNT(*) FROM member").fetchone()[0],
        "diagnosis_users": db.execute("SELECT COUNT(DISTINCT visit_id) FROM diagnosis_log").fetchone()[0],
        "official_clicks": db.execute("SELECT COUNT(*) FROM official_click").fetchone()[0],
    }
    return render_template("data.html", tables=TABLES, table=table, rows=rows, columns=columns,
                           prefectures=PREF_NAME, categories=gemini.CATEGORIES,
                           gemini_ready=bool(os.environ.get("GEMINI_API_KEY")),
                           difficulty_stats=difficulty_stats, subsidy_usage=subsidy_usage, metrics=metrics)


@app.route("/data/gemini", methods=["POST"])
def data_gemini():
    """Gemini に補助金を聞いて、確認画面に出す（まだ登録しない）"""
    if "admin_id" not in session:
        return redirect("/data/login")
    area = request.form.get("area", "")
    category = request.form.get("category", "")
    if area not in PREF_NAME or (category and category not in gemini.CATEGORIES):
        flash("地域またはカテゴリを選び直してください")
        return redirect("/data")
    try:
        items = gemini.fetch_subsidies(PREF_NAME[area], category)
    except Exception as e:
        flash(f"Gemini から取得できませんでした：{e}")
        return redirect("/data")
    return render_template("data_gemini.html", items=items, area=area)


@app.route("/data/gemini/save", methods=["POST"])
def data_gemini_save():
    """確認画面でチェックした補助金を登録する"""
    if "admin_id" not in session:
        return redirect("/data/login")
    area = request.form.get("area", "")
    if area not in PREF_NAME:
        flash("地域を選び直してください")
        return redirect("/data")

    selected = []
    for n in request.form.getlist("checked"):
        if not n.isdecimal():
            flash("登録する制度を選び直してください")
            return redirect("/data")
        try:
            name = request.form[f"name_{n}"].strip()
            amount = request.form[f"amount_{n}"].strip()
            difficulty = request.form[f"difficulty_{n}"]
            deadline = request.form.get(f"deadline_{n}", "").strip() or None
            official_url = request.form[f"official_url_{n}"].strip()
            category = request.form[f"category_{n}"]
            single_parent_only = request.form[f"single_parent_only_{n}"]
            child_required = request.form[f"child_required_{n}"]
            income_max = request.form.get(f"income_max_{n}", "").strip()
        except KeyError:
            flash("取得した制度情報が不足しています。もう一度取得してください")
            return redirect("/data")

        parsed_url = urlparse(official_url)
        if (not name or len(name) > 100 or not amount or len(amount) > 100
                or difficulty not in {"easy", "normal", "hard"}
                or category not in gemini.CATEGORIES
                or len(official_url) > 500 or parsed_url.scheme != "https" or not parsed_url.netloc
                or single_parent_only not in {"0", "1"}
                or child_required not in {"0", "1"}):
            flash("登録できない形式の制度情報が含まれています。取得し直してください")
            return redirect("/data")
        if deadline:
            try:
                if date.fromisoformat(deadline).isoformat() != deadline:
                    raise ValueError
            except ValueError:
                flash("申請期限の形式が正しくありません。取得し直してください")
                return redirect("/data")
        income_max_value = None
        if income_max and income_max != "0":
            if not income_max.isdecimal() or int(income_max) not in range(1, 5):
                flash("年収上限の形式が正しくありません。取得し直してください")
                return redirect("/data")
            income_max_value = int(income_max)
        selected.append((name, amount, difficulty, deadline, official_url, category,
                         int(single_parent_only), int(child_required),
                         income_max_value))

    db = get_db()
    count = 0
    skipped = 0
    for item in selected:
        exists = db.execute(
            "SELECT id FROM subsidy WHERE name = ? AND target_area = ?", (item[0], area)
        ).fetchone()
        if exists:
            skipped += 1
            continue
        db.execute(
            "INSERT INTO subsidy (name, amount, difficulty, deadline, official_url, category, target_area,"
            " single_parent_only, child_required, income_max, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (*item[:6], area, *item[6:], now()))
        count += 1
    db.commit()
    flash(f"{count} 件登録しました（重複 {skipped} 件は除外）")
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
