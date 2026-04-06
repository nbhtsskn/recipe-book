"""
batch_fetch.py — プレイリスト内の全動画を取得してデータを保存する
Usage: python batch_fetch.py <playlist_or_channel_URL>

既にrecipes.jsonに存在するIDはスキップする。
各動画のmeta情報とsubtitleをbatch_data/に保存する。
"""
import sys, json, os, re, subprocess, shutil

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BATCH_DIR = os.path.join(PROJECT_DIR, "batch_data")
RECIPES_DIR = os.path.join(PROJECT_DIR, "recipes")


def get_existing_ids():
    index_path = os.path.join(RECIPES_DIR, "recipes.json")
    with open(index_path, encoding="utf-8") as f:
        return {r["id"] for r in json.load(f)}


def get_playlist_ids(url):
    print("プレイリストの動画IDを取得中...")
    result = subprocess.run(
        ["yt-dlp", "--flat-playlist", "--print", "id", url],
        capture_output=True, text=True, encoding="utf-8"
    )
    ids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    print(f"  {len(ids)}本の動画を発見")
    return ids


def fetch_video(video_id, existing_ids):
    if video_id in existing_ids:
        print(f"  [{video_id}] スキップ（登録済み）")
        return False

    video_dir = os.path.join(BATCH_DIR, video_id)
    meta_path = os.path.join(video_dir, "meta.json")

    if os.path.exists(meta_path):
        print(f"  [{video_id}] スキップ（取得済み）")
        return True

    os.makedirs(video_dir, exist_ok=True)
    url = f"https://www.youtube.com/watch?v={video_id}"

    # 動画情報取得
    result = subprocess.run(
        ["yt-dlp", "--dump-json", "--skip-download", url],
        capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode != 0:
        print(f"  [{video_id}] 取得失敗: {result.stderr[:100]}")
        shutil.rmtree(video_dir, ignore_errors=True)
        return False

    info = json.loads(result.stdout)
    meta = {
        "id": info["id"],
        "title": info.get("title", ""),
        "channel": info.get("uploader", "") or info.get("channel", ""),
        "duration": info.get("duration", 0),
        "thumbnail": info.get("thumbnail", ""),
        "upload_date": info.get("upload_date", ""),
        "tags": (info.get("tags") or [])[:10],
        "description": info.get("description", "") or "",
        "webpage_url": info.get("webpage_url", url),
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # 字幕取得
    subprocess.run(
        ["yt-dlp", "--skip-download", "--write-auto-subs",
         "--sub-format", "vtt", "--sub-langs", "ja,en,zh",
         "-o", os.path.join(video_dir, "%(id)s.%(ext)s"), url],
        capture_output=True, text=True, encoding="utf-8"
    )

    # 字幕パース
    subtitles = {}
    for fname in os.listdir(video_dir):
        if fname.endswith(".vtt"):
            lang = fname.replace(video_id + ".", "").replace(".vtt", "").split(".")[-1]
            with open(os.path.join(video_dir, fname), encoding="utf-8") as f:
                raw = f.read()
            lines, seen = [], set()
            for line in raw.splitlines():
                line = line.strip()
                if not line or "-->" in line or line.startswith(("WEBVTT", "NOTE", "Kind:", "Language:")):
                    continue
                line = re.sub(r"<[^>]+>", "", line)
                if line and line not in seen:
                    seen.add(line)
                    lines.append(line)
            subtitles[lang] = "\n".join(lines)

    sub_path = os.path.join(video_dir, "subtitles.json")
    with open(sub_path, "w", encoding="utf-8") as f:
        json.dump(subtitles, f, ensure_ascii=False, indent=2)

    print(f"  [{video_id}] 取得完了: {meta['title'][:50]}")
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python batch_fetch.py <playlist_URL>")
        sys.exit(1)

    url = sys.argv[1]
    os.makedirs(BATCH_DIR, exist_ok=True)
    existing_ids = get_existing_ids()

    video_ids = get_playlist_ids(url)
    new_ids = [vid for vid in video_ids if vid not in existing_ids]
    print(f"\n新規追加対象: {len(new_ids)}本（登録済み: {len(video_ids) - len(new_ids)}本）\n")

    success = []
    for i, video_id in enumerate(new_ids, 1):
        print(f"[{i}/{len(new_ids)}] 処理中...")
        if fetch_video(video_id, existing_ids):
            success.append(video_id)

    # 処理待ちリストを保存
    pending_path = os.path.join(BATCH_DIR, "pending.json")
    with open(pending_path, "w", encoding="utf-8") as f:
        json.dump(success, f, ensure_ascii=False, indent=2)

    print(f"\n完了！ {len(success)}本のデータを取得しました。")
    print(f"次のステップ: Claudeにpending.jsonの内容を分析してもらいレシピを生成します。")


if __name__ == "__main__":
    main()
