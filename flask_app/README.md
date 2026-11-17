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
| templates/ | 画面のHTML（base.html と static/style.css を全画面で共通利用） |
| .env | Gemini のAPIキー（.env.example をコピーして作る。Gitには登録しない） |

## URL
| URL | 画面 |
|---|---|
| / | HOME |
| /diagnosis | 診断 |
| /result/番号 | 診断結果 |
| /register, /login | 新規登録・ログイン |
| /mypage | マイページ（保存制度・診断条件・通知設定） |
| /account | メールアドレス・パスワードの変更 |
| /data | データセンター（admin / admin、利用状況・難易度別クリック集計） |

## Gemini を使う
1. https://aistudio.google.com/apikey でAPIキーを作る（無料で使うため、課金は設定しない）
2. `flask_app/.env.example` を `flask_app/.env` にコピーし、実際のキーに置き換える
3. 起動し直すと、データセンターに「Geminiに聞く」が出る
4. 地域・カテゴリを選んで取得し、内容と公式URLを確認してから選択した制度だけDBへ登録する

Geminiの回答は誤りを含むことがあるため、確認前に自動登録しません。重複する制度は同じ地域のDBへ二重登録しません。

## 利用状況の集計
診断結果・マイページから公式サイトを開くとクリックを記録し、データセンターに難易度別・制度別のクリック数と訪問者数を表示します。利用者数は診断ログの訪問ID単位で数え、同じブラウザーからの複数クリックは訪問者数では1人として集計します。集計はこの機能を追加した後の操作から蓄積されます。
