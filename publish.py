#!/usr/bin/env python3
"""queue/ の先頭の投稿を Instagram に公開し、posted/ に移動する。

GitHub Actions から毎日呼ばれる想定。標準ライブラリのみで動く。

環境変数:
  IG_ACCESS_TOKEN  Instagram の長期アクセストークン（必須）
  IG_USER_ID       Instagram のユーザーID（省略時はトークンから取得）
  IMAGE_BASE_URL   画像を公開URLで取得するためのベースURL
                   （省略時は GitHub の raw URL を組み立てる）
  DRY_RUN=1        API を呼ばずに、何を投稿するかだけ表示する
"""
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://graph.instagram.com/" + os.environ.get("IG_API_VERSION", "v23.0")
ROOT = Path(__file__).resolve().parent
QUEUE = ROOT / "queue"
POSTED = ROOT / "posted"
IMAGE_EXTS = {".jpg", ".jpeg"}


def call(method, path, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        url, data = f"{url}?{data.decode()}", None
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        sys.exit(f"API エラー ({method} {path}): {e.code} {e.read().decode()}")


def next_post():
    """queue/ の中で名前順に一番先の投稿フォルダを返す。"""
    if not QUEUE.exists():
        return None
    for d in sorted(p for p in QUEUE.iterdir() if p.is_dir()):
        images = sorted(p for p in d.iterdir() if p.suffix.lower() in IMAGE_EXTS)
        if images:
            return d, images
        print(f"スキップ: {d.name} に JPEG 画像がありません")
    return None


def image_url(path):
    rel = path.relative_to(ROOT).as_posix()
    base = os.environ.get("IMAGE_BASE_URL")
    if not base:
        repo = os.environ["GITHUB_REPOSITORY"]
        sha = os.environ.get("GITHUB_SHA", "main")
        base = f"https://raw.githubusercontent.com/{repo}/{sha}"
    return f"{base.rstrip('/')}/{urllib.parse.quote(rel)}"


def wait_ready(container_id):
    for _ in range(30):
        status = call("GET", container_id, fields="status_code").get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            sys.exit(f"メディアの処理に失敗しました: {container_id} ({status})")
        time.sleep(5)
    sys.exit(f"メディアの処理がタイムアウトしました: {container_id}")


def publish(user_id, images, caption):
    if len(images) == 1:
        creation = call("POST", f"{user_id}/media",
                        image_url=image_url(images[0]), caption=caption)["id"]
    else:
        children = []
        for img in images[:10]:
            cid = call("POST", f"{user_id}/media",
                       image_url=image_url(img), is_carousel_item="true")["id"]
            wait_ready(cid)
            children.append(cid)
        creation = call("POST", f"{user_id}/media", media_type="CAROUSEL",
                        children=",".join(children), caption=caption)["id"]
    wait_ready(creation)
    return call("POST", f"{user_id}/media_publish", creation_id=creation)["id"]


def main():
    found = next_post()
    if not found:
        print("queue/ に投稿がありません。今日はスキップします。")
        return
    folder, images = found
    caption_file = folder / "caption.txt"
    caption = caption_file.read_text(encoding="utf-8").strip() if caption_file.exists() else ""

    print(f"投稿: {folder.name}（画像 {len(images)} 枚）")
    print(caption)
    if os.environ.get("DRY_RUN") == "1":
        for img in images:
            print("  画像URL:", image_url(img))
        print("DRY_RUN のため投稿しません。")
        return

    user_id = os.environ.get("IG_USER_ID") or call("GET", "me", fields="user_id")["user_id"]
    media_id = publish(user_id, images, caption)
    print(f"公開しました: media_id={media_id}")

    POSTED.mkdir(exist_ok=True)
    shutil.move(str(folder), str(POSTED / folder.name))


if __name__ == "__main__":
    main()
