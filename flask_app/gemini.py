"""Gemini API に補助金を聞く

APIキーは flask_app/.env に  GEMINI_API_KEY=キー  と書く。
無料で使うには、APIキーを作る Google のプロジェクトに課金（請求先アカウント）を設定しないこと。
"""
import json
import os
import urllib.request

MODEL = "gemini-2.5-flash"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

CATEGORIES = ["子育て", "お金", "住まい", "教育", "仕事", "ひとり親支援"]


def load_env():
    """.env ファイルの  KEY=VALUE  を環境変数に読み込む"""
    if not os.path.exists(".env"):
        return
    for line in open(".env", encoding="utf-8"):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()


def fetch_subsidies(area_name, category):
    """Gemini に聞いて、補助金の辞書のリストを返す"""
    prompt = f"""日本の{area_name}で、子育て家庭が使える補助金・手当を5件、JSONの配列だけで答えてください。
カテゴリ：{category or "指定なし"}
実在する制度だけにしてください。各要素は次の形です。
{{
  "name": "制度名",
  "amount": "もらえる金額の目安（例：月1万円）",
  "difficulty": "easy か normal か hard",
  "deadline": "申請期限 YYYY-MM-DD（決まっていなければ空文字）",
  "official_url": "公式サイトのURL",
  "category": "{'／'.join(CATEGORIES)} のどれか",
  "single_parent_only": ひとり親だけが対象なら 1、違えば 0,
  "child_required": 子どもがいることが条件なら 1、違えば 0,
  "income_max": 年収の上限区分 1〜4（所得制限なしは 0）
}}"""

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},   # JSONで返してもらう
    }
    request = urllib.request.Request(
        URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.loads(response.read())

    text = result["candidates"][0]["content"]["parts"][0]["text"]
    items = json.loads(text)

    # 使えない値をはじく・直す
    good = []
    for item in items:
        if not str(item.get("official_url", "")).startswith("https://"):
            continue                                   # 公式URLがおかしいものは使わない
        if item.get("difficulty") not in ["easy", "normal", "hard"]:
            item["difficulty"] = "normal"
        if item.get("category") not in CATEGORIES:
            item["category"] = "子育て"
        good.append(item)
    return good
