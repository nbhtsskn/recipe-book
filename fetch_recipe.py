"""
fetch_recipe.py — レシピ動画からJSON+HTMLを生成するスクリプト
Usage: python fetch_recipe.py <YouTube_URL>
"""
import sys
import json
import os
import re
import subprocess
import tempfile
import shutil
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
RECIPES_DIR = os.path.join(PROJECT_DIR, "recipes")

# ─────────────────────────────────────────────
# 1. yt-dlp で動画情報・字幕を取得
# ─────────────────────────────────────────────

def fetch_video_info(url):
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--skip-download",
        url
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp error:\n{result.stderr}")
    return json.loads(result.stdout)

def fetch_subtitles(url, video_id, tmp_dir):
    """自動生成字幕を全言語取得"""
    cmd = [
        "yt-dlp",
        "--skip-download",
        "--write-auto-subs",
        "--sub-format", "vtt",
        "--sub-langs", "all",
        "-o", os.path.join(tmp_dir, "%(id)s.%(ext)s"),
        url
    ]
    subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

    subtitles = {}
    for fname in os.listdir(tmp_dir):
        if fname.endswith(".vtt") and video_id in fname:
            # 言語コード抽出: videoId.ja.vtt など
            parts = fname.replace(video_id + ".", "").replace(".vtt", "")
            lang = parts.split(".")[-1]
            fpath = os.path.join(tmp_dir, fname)
            with open(fpath, encoding="utf-8") as f:
                raw = f.read()
            subtitles[lang] = parse_vtt(raw)
    return subtitles

def parse_vtt(vtt_text):
    """VTT字幕テキストをプレーンテキストに変換（重複除去）"""
    lines = []
    seen = set()
    for line in vtt_text.splitlines():
        line = line.strip()
        if not line or "-->" in line or line.startswith("WEBVTT") or line.startswith("NOTE"):
            continue
        # HTMLタグ除去
        line = re.sub(r"<[^>]+>", "", line)
        if line and line not in seen:
            seen.add(line)
            lines.append(line)
    return "\n".join(lines)

# ─────────────────────────────────────────────
# 2. 概要欄からレシピ情報を解析
# ─────────────────────────────────────────────

def parse_recipe_from_description(desc):
    """概要欄から材料・手順をヒューリスティック抽出"""
    ingredients = []
    steps = []

    # 一般的な区切りパターン
    ingredient_headers = re.compile(
        r"(材料|Ingredients?|食材|원재료|Zutaten|Ingrédients?|Ingredienti|Ingredientes?)\s*[:\uff1a]?",
        re.IGNORECASE
    )
    step_headers = re.compile(
        r"(作り方|手順|Steps?|Instructions?|Directions?|Zubereitung|Préparation|Preparazione|Preparación|조리법)\s*[:\uff1a]?",
        re.IGNORECASE
    )

    lines = desc.splitlines()
    mode = None
    step_num = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if ingredient_headers.search(line):
            mode = "ingredients"
            continue
        if step_headers.search(line):
            mode = "steps"
            step_num = 0
            continue

        if mode == "ingredients":
            # 番号・記号付きリストを除去
            clean = re.sub(r"^[\-\*•・\d\.]+\s*", "", line).strip()
            if clean:
                # 量と材料名を分割しようと試みる
                m = re.match(r"^(.+?)\s+([\d/½¼¾]+\s*[a-zA-Zg㎖cc大小さじ杯個本枚缶袋]+.*)", clean)
                if m:
                    ingredients.append({"name": m.group(1).strip(), "amount": m.group(2).strip()})
                else:
                    ingredients.append({"name": clean, "amount": ""})
        elif mode == "steps":
            clean = re.sub(r"^[\-\*•・\d\.]+\s*", "", line).strip()
            if clean:
                step_num += 1
                steps.append({"step": step_num, "text": clean})

    return ingredients, steps

def format_duration(seconds):
    if not seconds:
        return ""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

# ─────────────────────────────────────────────
# 3. JSON生成
# ─────────────────────────────────────────────

def build_recipe_json(info, subtitles):
    desc = info.get("description", "") or ""
    ingredients, steps = parse_recipe_from_description(desc)

    recipe = {
        "id": info["id"],
        "title": info.get("title", ""),
        "channel": info.get("uploader", "") or info.get("channel", ""),
        "url": info.get("webpage_url", ""),
        "thumbnail": info.get("thumbnail", ""),
        "duration": format_duration(info.get("duration")),
        "upload_date": info.get("upload_date", ""),
        "added_at": datetime.now().strftime("%Y-%m-%d"),
        "tags": (info.get("tags") or [])[:10],
        "description": desc,
        "ingredients": ingredients,
        "steps": steps,
        "subtitles": subtitles,
    }
    return recipe

# ─────────────────────────────────────────────
# 4. HTMLレシピページ生成
# ─────────────────────────────────────────────

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — My Recipe Book</title>
  <link rel="stylesheet" href="../assets/style.css">
</head>
<body>
  <div class="recipe-detail">
    <a class="back-link" href="../index.html">← レシピ一覧に戻る</a>

    <div class="recipe-hero">
      {thumbnail_html}
      <div class="recipe-hero-body">
        <h1>{title}</h1>
        <div class="recipe-meta">
          <span>📺 {channel}</span>
          {duration_html}
          <span>📅 {added_at}</span>
        </div>
        <div class="recipe-source">
          <a href="{url}" target="_blank" rel="noopener">▶ 元動画を見る</a>
        </div>
      </div>
    </div>

    {recipe_sections}

    {description_html}

    {subtitle_html}
  </div>

  <script>
    function showLang(lang) {{
      document.querySelectorAll('.lang-panel').forEach(p => p.style.display = 'none');
      document.querySelectorAll('.lang-tab').forEach(t => t.classList.remove('active'));
      const panel = document.getElementById('lang-' + lang);
      if (panel) panel.style.display = 'block';
      const tab = document.querySelector('.lang-tab[data-lang="' + lang + '"]');
      if (tab) tab.classList.add('active');
    }}
    // 最初のタブを表示
    const firstTab = document.querySelector('.lang-tab');
    if (firstTab) showLang(firstTab.dataset.lang);
  </script>
</body>
</html>
"""

def escape_html(s):
    return str(s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def build_recipe_html(recipe):
    title = escape_html(recipe["title"])
    channel = escape_html(recipe["channel"])
    url = escape_html(recipe["url"])
    added_at = escape_html(recipe["added_at"])

    thumbnail_html = ""
    if recipe.get("thumbnail"):
        thumbnail_html = f'<img src="{escape_html(recipe["thumbnail"])}" alt="{title}">'

    duration_html = f'<span>⏱ {escape_html(recipe["duration"])}</span>' if recipe.get("duration") else ""

    # 材料・手順セクション
    recipe_sections = ""
    has_ingredients = bool(recipe.get("ingredients"))
    has_steps = bool(recipe.get("steps"))

    if has_ingredients or has_steps:
        ingredients_html = ""
        if has_ingredients:
            items = "".join(
                f'<li><span class="ingredient-amount">{escape_html(i["amount"])}</span>{escape_html(i["name"])}</li>'
                for i in recipe["ingredients"]
            )
            ingredients_html = f"""
            <div class="recipe-section">
              <h2>🥕 材料 / Ingredients</h2>
              <ul class="ingredients-list">{items}</ul>
            </div>"""

        steps_html = ""
        if has_steps:
            cards = []
            for s in recipe["steps"]:
                point_html = ""
                if s.get("point"):
                    point_html = f'<div class="step-point"><span class="point-label">💡 ポイント</span>{escape_html(s["point"])}</div>'
                cards.append(
                    f'<li class="step-card">'
                    f'<div class="step-header"><span class="step-num">{s["step"]}</span>'
                    f'<span class="step-text">{escape_html(s["text"])}</span></div>'
                    f'{point_html}</li>'
                )
            steps_html = f"""
            <div class="recipe-section">
              <h2>👨‍🍳 手順 / Steps</h2>
              <ul class="steps-list">{"".join(cards)}</ul>
            </div>"""

        recipe_sections = f'<div class="recipe-sections">{ingredients_html}{steps_html}</div>'

    # 概要欄
    description_html = ""
    if recipe.get("description"):
        description_html = f"""
    <div class="description-section">
      <h2>📝 概要欄 / Description</h2>
      <div class="description-content">{escape_html(recipe["description"])}</div>
    </div>"""

    # 字幕セクション
    subtitle_html = ""
    subtitles = recipe.get("subtitles", {})
    if subtitles:
        tabs = "".join(
            f'<button class="lang-tab" data-lang="{escape_html(lang)}" onclick="showLang(\'{escape_html(lang)}\')">{escape_html(lang.upper())}</button>'
            for lang in subtitles
        )
        panels = "".join(
            f'<div class="lang-panel" id="lang-{escape_html(lang)}" style="display:none"><div class="subtitle-content">{escape_html(text)}</div></div>'
            for lang, text in subtitles.items()
        )
        subtitle_html = f"""
    <div class="subtitle-section">
      <h2>💬 字幕 / Subtitles</h2>
      <div class="subtitle-lang-tabs">{tabs}</div>
      {panels}
    </div>"""

    return HTML_TEMPLATE.format(
        title=title,
        channel=channel,
        url=url,
        added_at=added_at,
        thumbnail_html=thumbnail_html,
        duration_html=duration_html,
        recipe_sections=recipe_sections,
        description_html=description_html,
        subtitle_html=subtitle_html,
    )

# ─────────────────────────────────────────────
# 5. recipes.json インデックス更新
# ─────────────────────────────────────────────

def update_index(recipe):
    index_path = os.path.join(RECIPES_DIR, "recipes.json")
    with open(index_path, encoding="utf-8") as f:
        index = json.load(f)

    # 同IDがあれば更新、なければ追加
    existing_ids = [r["id"] for r in index]
    entry = {
        "id": recipe["id"],
        "title": recipe["title"],
        "channel": recipe["channel"],
        "thumbnail": recipe["thumbnail"],
        "duration": recipe["duration"],
        "added_at": recipe["added_at"],
        "tags": recipe["tags"],
        "url": recipe["url"],
    }
    if recipe["id"] in existing_ids:
        index = [entry if r["id"] == recipe["id"] else r for r in index]
    else:
        index.insert(0, entry)

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

# ─────────────────────────────────────────────
# 6. メイン
# ─────────────────────────────────────────────

def main(url):
    print(f"[1/4] 動画情報を取得中: {url}")
    info = fetch_video_info(url)
    video_id = info["id"]
    print(f"      タイトル: {info.get('title', '')}")

    print("[2/4] 字幕を取得中...")
    tmp_dir = tempfile.mkdtemp()
    try:
        subtitles = fetch_subtitles(url, video_id, tmp_dir)
        print(f"      取得した言語: {list(subtitles.keys()) or '(なし)'}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print("[3/4] JSONを生成中...")
    recipe = build_recipe_json(info, subtitles)
    json_path = os.path.join(RECIPES_DIR, f"{video_id}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(recipe, f, ensure_ascii=False, indent=2)
    print(f"      保存: {json_path}")

    print("[4/4] HTMLを生成中...")
    html_content = build_recipe_html(recipe)
    html_path = os.path.join(RECIPES_DIR, f"{video_id}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"      保存: {html_path}")

    update_index(recipe)
    print(f"\n完了! ブラウザで開く: {os.path.join(PROJECT_DIR, 'index.html')}")
    return recipe

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_recipe.py <YouTube_URL>")
        sys.exit(1)
    main(sys.argv[1])
