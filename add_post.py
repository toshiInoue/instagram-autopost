#!/usr/bin/env python3
"""写真とキャプションから queue/ に投稿を1件追加する（Mac 用）。

Instagram の条件に合わせて、macOS 標準の sips で
  - JPEG に変換（HEIC / PNG もOK）
  - 縦横比を 4:5〜1.91:1 に中央トリミング（iPhone の縦写真 3:4 は 4:5 に）
  - 横幅 1440px 以下に縮小
してから保存する。

使い方:
  python3 add_post.py 写真1.jpg [写真2.jpg ...] -c "キャプション"
  python3 add_post.py 写真*.HEIC -f caption.txt -n mustang
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MIN_RATIO, MAX_RATIO = 4 / 5, 1.91  # 幅 / 高さ
MAX_WIDTH = 1440


def size(path):
    out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
                         capture_output=True, text=True, check=True).stdout
    w = int(re.search(r"pixelWidth: (\d+)", out).group(1))
    h = int(re.search(r"pixelHeight: (\d+)", out).group(1))
    return w, h


def sips(*args):
    subprocess.run(["sips", *map(str, args)], capture_output=True, check=True)


def prepare(src, dst):
    sips("-s", "format", "jpeg", "-s", "formatOptions", "85", src, "--out", dst)
    w, h = size(dst)
    if w / h < MIN_RATIO:
        sips("-c", int(w / MIN_RATIO), w, dst)
    elif w / h > MAX_RATIO:
        sips("-c", h, int(h * MAX_RATIO), dst)
    w, _ = size(dst)
    if w > MAX_WIDTH:
        sips("--resampleWidth", MAX_WIDTH, dst)


def next_number():
    nums = [int(m.group(1)) for d in ("queue", "posted") if (ROOT / d).exists()
            for p in (ROOT / d).iterdir() if (m := re.match(r"(\d+)", p.name))]
    return max(nums, default=0) + 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+", type=Path, help="写真（最大10枚。2枚以上でカルーセル投稿）")
    ap.add_argument("-c", "--caption", help="キャプション")
    ap.add_argument("-f", "--caption-file", type=Path, help="キャプションを書いたテキストファイル")
    ap.add_argument("-n", "--name", default="post", help="フォルダ名に付ける短い名前（英数字）")
    args = ap.parse_args()

    if len(args.images) > 10:
        sys.exit("1投稿の画像は最大10枚です")
    caption = args.caption or (args.caption_file.read_text(encoding="utf-8") if args.caption_file else "")
    if len(caption) > 2200:
        sys.exit(f"キャプションが長すぎます（{len(caption)} 文字 / 上限 2200）")

    folder = ROOT / "queue" / f"{next_number():03d}-{args.name}"
    folder.mkdir(parents=True)
    for i, src in enumerate(args.images, 1):
        prepare(src, folder / f"{i:02d}.jpg")
    (folder / "caption.txt").write_text(caption.strip() + "\n", encoding="utf-8")
    print(f"追加しました: {folder.relative_to(ROOT)}（画像 {len(args.images)} 枚）")


if __name__ == "__main__":
    main()
