/* ぽけっと手当 共通スクリプト
   テーブル設計書（26_テーブル設計書_ぽけっと手当.xlsx）の4テーブルを localStorage で再現する
   subsidy（補助金マスタ）／member（会員）／favorite（お気に入り）／diagnosis_log（診断ログ） */

// ---------------- コード値（画面設計書の Value属性）
const PREFS = ["北海道","青森県","岩手県","宮城県","秋田県","山形県","福島県","茨城県","栃木県","群馬県",
  "埼玉県","千葉県","東京都","神奈川県","新潟県","富山県","石川県","福井県","山梨県","長野県","岐阜県",
  "静岡県","愛知県","三重県","滋賀県","京都府","大阪府","兵庫県","奈良県","和歌山県","鳥取県","島根県",
  "岡山県","広島県","山口県","徳島県","香川県","愛媛県","高知県","福岡県","佐賀県","長崎県","熊本県",
  "大分県","宮崎県","鹿児島県","沖縄県"].map((n, i) => [String(i + 1).padStart(2, "0"), n]);
const PREF_NAME = Object.fromEntries([["00", "全国"], ...PREFS]);
const CHILDREN = [[0, "0人"], [1, "1人"], [2, "2人"], [3, "3人"], [4, "4人以上"]];
const INCOMES = [[1, "300万円未満"], [2, "300〜500万円"], [3, "500〜800万円"], [4, "800万円以上"], [5, "わからない"]];
const SINGLE = [[1, "はい"], [0, "いいえ"]];
const DIFF_LABEL = { easy: "簡単", normal: "普通", hard: "難しい" };

// ---------------- 補助金マスタのサンプル（seed.py と同じ内容。deadline は今日からの日数）
const CFA = "https://www.cfa.go.jp/policies/hitori-oya/";
const SUBSIDY_SEED = [
  ["児童手当", "子育て", "easy", "月1万円〜／1人", "https://www.cfa.go.jp/policies/kokoseido/jidouteate/"],
  ["子ども医療費助成（市区町村）", "子育て", "easy", "医療費の自己負担を助成", "https://www.cfa.go.jp/"],
  ["幼児教育・保育の無償化", "子育て", "easy", "3〜5歳の保育料0円", "https://www.cfa.go.jp/policies/kokoseido/mushouka/"],
  ["出産育児一時金", "子育て", "easy", "1児につき50万円", "https://www.mhlw.go.jp/", { child_required: false }],
  ["就学援助（市区町村）", "教育", "normal", "学用品費・給食費など", "https://www.mext.go.jp/", { deadline: 4, income_max: 2 }],
  ["高等学校等就学支援金", "教育", "normal", "年11万8,800円〜", "https://www.mext.go.jp/", { deadline: 20, income_max: 3 }],
  ["高校生等奨学給付金", "教育", "normal", "年3万2,300円〜", "https://www.mext.go.jp/", { deadline: 45, income_max: 1 }],
  ["高等教育の修学支援新制度", "教育", "hard", "授業料の減免＋給付型奨学金", "https://www.mext.go.jp/kyufu/", { deadline: 60, income_max: 2 }],
  ["子育て世帯の住み替え補助（市区町村）", "住まい", "normal", "最大10万円", "https://www.mlit.go.jp/", { deadline: 6 }],
  ["住居確保給付金", "住まい", "hard", "家賃相当額（上限あり）", "https://www.mhlw.go.jp/", { child_required: false, income_max: 1 }],
  ["児童扶養手当", "ひとり親支援", "normal", "月最大4万6,690円（1人目）", CFA, { single_parent_only: true, income_max: 2 }],
  ["ひとり親家庭等医療費助成（市区町村）", "ひとり親支援", "normal", "医療費の自己負担を助成", CFA, { single_parent_only: true, income_max: 2 }],
  ["高等職業訓練促進給付金", "仕事", "hard", "月10万円（非課税世帯は月14万円）", CFA, { single_parent_only: true, income_max: 2 }],
  ["育児休業給付金", "仕事", "normal", "休業前の賃金の67%", "https://www.mhlw.go.jp/", { child_required: false }],
  ["018サポート（東京都）", "お金", "easy", "月5,000円／1人", "https://www.fukushi.metro.tokyo.lg.jp/", { target_area: "13" }],
  ["子育て応援臨時給付金（受付終了のサンプル）", "お金", "easy", "1人あたり5万円", "https://www.cfa.go.jp/", { deadline: -10 }],
];

// ---------------- 日付
const pad = n => String(n).padStart(2, "0");
const ymd = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const today = () => { const d = new Date(); d.setHours(0, 0, 0, 0); return d; };
const addDays = n => { const d = today(); d.setDate(d.getDate() + n); return ymd(d); };
const daysLeft = s => Math.round((new Date(s + "T00:00:00") - today()) / 86400000);
const now = () => new Date().toISOString();

// ---------------- DB（localStorage）
const DB_KEY = "pokette_db";
function loadDB() {
  let db = JSON.parse(localStorage.getItem(DB_KEY) || "null");
  if (!db) {
    db = { seq: {}, subsidy: [], member: [], favorite: [], diagnosis_log: [] };
    SUBSIDY_SEED.forEach(([name, category, difficulty, amount, official_url, o = {}]) => {
      insert(db, "subsidy", {
        name, amount, difficulty, official_url, category,
        deadline: o.deadline === undefined ? null : addDays(o.deadline),
        target_area: o.target_area || "00",
        single_parent_only: !!o.single_parent_only,
        child_required: o.child_required !== false,
        income_max: o.income_max || null,
        updated_at: now(),
      });
    });
    saveDB(db);
  }
  return db;
}
function saveDB(db) { localStorage.setItem(DB_KEY, JSON.stringify(db)); }
function insert(db, table, row) {
  db.seq[table] = (db.seq[table] || 0) + 1;
  row = { id: db.seq[table], ...row };
  db[table].push(row);
  return row;
}
function resetDB() {
  [DB_KEY, "pokette_login", "pokette_tmp_fav", "pokette_last_diag"].forEach(k => localStorage.removeItem(k));
  location.href = "index.html";
}

// ---------------- 訪問ID・ログイン状態
function visitId() {
  let v = localStorage.getItem("pokette_visit");
  if (!v) {
    v = crypto.randomUUID ? crypto.randomUUID() : "v-" + Date.now() + "-" + Math.random().toString(16).slice(2);
    localStorage.setItem("pokette_visit", v);
  }
  return v;
}
function currentMember(db = loadDB()) {
  const id = Number(localStorage.getItem("pokette_login"));
  return db.member.find(m => m.id === id) || null;
}
async function hashPassword(pw) {  // 本番は werkzeug。ここでは SHA-256 で代用
  if (!crypto.subtle) return "plain:" + btoa(unescape(encodeURIComponent(pw))); // 非対応環境用（デモのみ）
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(pw));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("");
}

// ---------------- お気に入り（未ログインはブラウザに一時保存）
const tmpFav = () => JSON.parse(localStorage.getItem("pokette_tmp_fav") || "[]");
function isFavorite(db, subsidyId) {
  const m = currentMember(db);
  return m ? db.favorite.some(f => f.member_id === m.id && f.subsidy_id === subsidyId) : tmpFav().includes(subsidyId);
}
function toggleFavorite(subsidyId) {
  const db = loadDB(), m = currentMember(db);
  if (m) {
    const i = db.favorite.findIndex(f => f.member_id === m.id && f.subsidy_id === subsidyId);
    if (i >= 0) db.favorite.splice(i, 1);
    else insert(db, "favorite", { member_id: m.id, subsidy_id: subsidyId, created_at: ymd(new Date()) });
    saveDB(db);
  } else {
    const t = tmpFav(), i = t.indexOf(subsidyId);
    i >= 0 ? t.splice(i, 1) : t.push(subsidyId);
    localStorage.setItem("pokette_tmp_fav", JSON.stringify(t));
  }
}
// 登録・ログイン時に一時保存の☆と診断条件を会員へ引き継ぐ
function carryOver(db, member) {
  tmpFav().forEach(sid => {
    if (!db.favorite.some(f => f.member_id === member.id && f.subsidy_id === sid))
      insert(db, "favorite", { member_id: member.id, subsidy_id: sid, created_at: ymd(new Date()) });
  });
  localStorage.removeItem("pokette_tmp_fav");
  const log = db.diagnosis_log.find(l => l.id === Number(localStorage.getItem("pokette_last_diag")));
  if (log && log.member_id === null) {
    log.member_id = member.id;
    Object.assign(member, pickCond(log));
  }
}
const pickCond = l => ({ prefecture: l.prefecture, children_count: l.children_count, income: l.income, is_single: l.is_single });

// ---------------- 診断（共通仕様「判定ルール（簡易）」）
function match(s, c) {
  if (s.deadline && daysLeft(s.deadline) < 0) return false;                  // 期限切れは出さない
  if (s.target_area !== "00" && s.target_area !== c.prefecture) return false; // ①地域
  if (s.single_parent_only && !c.is_single) return false;                    // ②ひとり親限定
  if (s.child_required && c.children_count < 1) return false;                // ③子ども必須
  if (s.income_max && c.income !== 5 && c.income > s.income_max) return false; // ④年収（わからないは除外しない）
  return true;
}
// 申請期限が近い順。随時（NULL）は最後
const byDeadline = (a, b) => (a.deadline || "9999") < (b.deadline || "9999") ? -1 : 1;

function lastDiagnosis(db) {
  const m = currentMember(db);
  const logs = m ? db.diagnosis_log.filter(l => l.member_id === m.id)
                 : db.diagnosis_log.filter(l => l.id === Number(localStorage.getItem("pokette_last_diag")));
  return logs.sort((a, b) => b.id - a.id)[0] || null;
}
const condText = c => `${PREF_NAME[c.prefecture]}／子ども${CHILDREN.find(x => x[0] === c.children_count)[1]}／` +
  `${INCOMES.find(x => x[0] === c.income)[1]}／ひとり親：${c.is_single ? "はい" : "いいえ"}`;

// ---------------- 表示の部品
const esc = s => String(s).replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
function deadlineHtml(d) {
  if (!d) return "随時";
  const n = daysLeft(d), md = `${d.slice(5, 7)}/${d.slice(8, 10)}`;
  return n <= 7 ? `<span class="urgent">${md}（あと${n}日）</span>` : md;
}
function header({ back } = {}) {
  const m = currentMember();
  document.getElementById("header").innerHTML = `
    ${back ? `<a class="back" href="${back}" aria-label="戻る">＜</a>` : ""}
    <a class="logo" href="index.html">ぽけっと手当</a>
    <a class="head-link" href="${m ? "mypage.html" : "auth.html?mode=login"}">${m ? "マイページ" : "ログイン"}</a>`;
}
function flash() {  // 前の画面からのメッセージ
  const msg = sessionStorage.getItem("pokette_flash");
  if (msg) {
    sessionStorage.removeItem("pokette_flash");
    document.querySelector("main").insertAdjacentHTML("afterbegin", `<p class="msg ok">${esc(msg)}</p>`);
  }
}
const setFlash = msg => sessionStorage.setItem("pokette_flash", msg);
