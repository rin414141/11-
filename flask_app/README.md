# ぽけっと手当（シンプル版）

## 起動
    pip install flask
    python app.py
ブラウザで http://127.0.0.1:5000/ を開く。初回起動で pokette.db ができる。
データを最初からにしたいときは pokette.db を消してから起動する。

## ファイル
| ファイル | 中身 |
|---|---|
| app.py | 画面ごとの処理（URL → 処理 → 画面） |
| gemini.py | Gemini API に補助金を聞く |
| schema.sql | テーブルを作るSQL |
| seed.sql | 補助金のサンプルデータ |
| templates/ | 画面のHTML（base.html が全画面共通の部分） |
| .env | Gemini のAPIキー（.env.example をコピーして作る） |

## URL
| URL | 画面 |
|---|---|
| / | HOME |
| /diagnosis | 診断 |
| /result/番号 | 診断結果 |
| /register, /login | 新規登録・ログイン |
| /mypage | マイページ |
| /data | データセンター（admin / admin） |

## Gemini を使う
1. https://aistudio.google.com/apikey でAPIキーを作る（無料で使うため、課金は設定しない）
2. .env.example をコピーして .env にし、キーを書く
3. 起動し直すと、データセンターに「Geminiに聞く」が出る
