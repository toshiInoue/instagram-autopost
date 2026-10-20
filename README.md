# Instagram 自動投稿

`queue/` に入れた投稿を、**毎日 19:00（日本時間）に1件ずつ** Instagram に自動投稿する仕組み。
GitHub Actions で動くので、Mac がスリープしていても投稿される。

- 投稿が終わったフォルダは自動で `posted/` に移動する
- `queue/` が空の日は何もしない
- 画像が2枚以上ならカルーセル投稿（最大10枚）

> まず個人アカウントで動作確認 → 問題なければ AUTO DEALER のアカウントに切り替える想定。
> 切り替えはトークン（`IG_ACCESS_TOKEN` / `IG_USER_ID`）を差し替えるだけ。

---

## 初回セットアップ（1回だけ）

### 1. Instagram をプロアカウントにする
Instagram アプリ → 設定 → 「アカウントの種類とツール」→ **プロアカウントに切り替える**（クリエイターでOK、無料）。
API での投稿はプロアカウントのみ対応。Facebook ページとの連携は不要。

### 2. Meta のアプリを作ってトークンを取る
1. https://developers.facebook.com/apps でアプリを作成（ユースケース：**Instagram の API を使ってメッセージ・コンテンツを管理**）
2. 左メニュー「Instagram の API（Instagram ログイン）」→ **API 設定** を開く
3. 「アクセストークンを生成」で自分の Instagram アカウントを追加 → ログインして許可
   - 権限に `instagram_business_basic` と `instagram_business_content_publish` が入っていること
4. 表示された **アクセストークン**（長期トークン・60日有効）と **Instagram ユーザーID** をメモ
   - アプリは「開発モード」のままでOK（自分のアカウントにだけ投稿するなら審査不要）

### 3. GitHub にリポジトリを作る
画像は GitHub の公開URL 経由で Instagram に渡すので、**リポジトリは Public** にする
（投稿予定の写真とキャプションが見える状態になる点だけ注意）。

```bash
gh auth login
```

```bash
cd ~/instagram-company && git init && git add -A && git commit -m "初期セットアップ" && gh repo create instagram-auto --public --source . --push
```

### 4. トークンを GitHub に登録（自分で入力）
GitHub のリポジトリ → Settings → Secrets and variables → Actions → **New repository secret**

| 名前 | 値 |
|---|---|
| `IG_ACCESS_TOKEN` | 手順2のアクセストークン |
| `IG_USER_ID` | 手順2の Instagram ユーザーID |
| `GH_PAT`（任意） | トークン自動更新用。GitHub の Fine-grained token（このリポジトリの **Secrets: Read and write** 権限） |

`GH_PAT` が無くても毎週トークンの延長はされる（多くの場合トークン文字列は変わらない）。
もし「トークン更新」ワークフローが失敗したら、手順2でトークンを取り直して `IG_ACCESS_TOKEN` を上書きする。

### 5. テスト
1. 投稿を1件追加して push（下の「投稿を追加する」参照）
2. GitHub → Actions → **Instagram 毎日投稿** → Run workflow
   - `投稿せずに確認だけする` にチェック → 画像URLとキャプションがログに出ればOK
   - チェックを外して実行 → 実際に投稿される

---

## 投稿を追加する

```bash
cd ~/instagram-company && python3 add_post.py ~/Downloads/IMG_3932.JPG -c "キャプション #ハッシュタグ" -n mustang
```

- 写真を複数並べるとカルーセル投稿になる
- HEIC / PNG も自動で JPEG に変換、Instagram の比率（4:5〜1.91:1）に中央トリミング、横1440px に縮小
- 長いキャプションは `-f caption.txt` でファイルから読める
- `queue/001-mustang/` のように番号付きフォルダができ、**番号の小さい順に投稿**される
- キャプションは後から `queue/<フォルダ>/caption.txt` を直接編集してもOK

追加したら GitHub に送る：

```bash
cd ~/instagram-company && git add -A && git commit -m "投稿追加" && git push
```

---

## ファイル構成

| ファイル | 役割 |
|---|---|
| `publish.py` | `queue/` の先頭を投稿して `posted/` に移す（Actions から実行） |
| `add_post.py` | 写真を整形して `queue/` に投稿を追加（Mac で実行） |
| `.github/workflows/post.yml` | 毎日 19:00 に `publish.py` を実行 |
| `.github/workflows/refresh-token.yml` | 毎週月曜にトークンを延長 |

投稿時刻を変えるときは `post.yml` の `cron` を編集（UTC 表記。日本時間 − 9時間）。

## 制限
- 1アカウントあたり 24時間で 100投稿まで（毎日1件なら関係なし）
- リール・ストーリーズは未対応（写真・カルーセルのみ）
