"""
make_recipe.py
video_info.json + subtitles/ を読み込んでレシピJSON+HTMLを生成し、
recipes/ と index.html を更新する。

引数なしで実行: python make_recipe.py
"""
import json, os, re
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
RECIPES_DIR = os.path.join(PROJECT_DIR, "recipes")

# ── 字幕パース ───────────────────────────────────────────
def parse_vtt(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    lines, seen = [], set()
    for line in raw.splitlines():
        line = line.strip()
        if not line or "-->" in line or line.startswith(("WEBVTT","NOTE","Kind:","Language:")):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        if line and line not in seen:
            seen.add(line)
            lines.append(line)
    return "\n".join(lines)

def load_subtitles(video_id):
    sub_dir = os.path.join(PROJECT_DIR, "subtitles")
    subs = {}
    if not os.path.isdir(sub_dir):
        return subs
    for fname in os.listdir(sub_dir):
        if fname.endswith(".vtt") and video_id in fname:
            lang = fname.replace(video_id + ".", "").replace(".vtt", "").split(".")[-1]
            subs[lang] = parse_vtt(os.path.join(sub_dir, fname))
    return subs

def format_duration(seconds):
    if not seconds: return ""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

# ── HTML生成 ─────────────────────────────────────────────
def esc(s):
    return str(s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def build_html(r):
    title  = esc(r["title"])
    thumb  = f'<img src="{esc(r["thumbnail"])}" alt="{title}">' if r.get("thumbnail") else ""
    dur    = f'<span>⏱ {esc(r["duration"])}</span>' if r.get("duration") else ""

    # 材料
    ing_items = "".join(
        f'<li><span class="ingredient-amount">{esc(i["amount"])}</span>{esc(i["name"])}</li>'
        for i in r.get("ingredients", [])
    )
    ing_html = (
        f'<div class="recipe-section"><h2>🥕 材料 / Ingredients</h2>'
        f'<ul class="ingredients-list">{ing_items}</ul></div>'
    ) if ing_items else ""

    # 手順
    cards = []
    for s in r.get("steps", []):
        pt = (
            f'<div class="step-point"><span class="point-label">💡 ポイント</span>{esc(s["point"])}</div>'
            if s.get("point") else ""
        )
        cards.append(
            f'<li class="step-card">'
            f'<div class="step-header"><span class="step-num">{s["step"]}</span>'
            f'<span class="step-text">{esc(s["text"])}</span></div>{pt}</li>'
        )
    step_html = (
        f'<div class="recipe-section"><h2>👨‍🍳 手順 / Steps</h2>'
        f'<ul class="steps-list">{"".join(cards)}</ul></div>'
    ) if cards else ""

    # 概要欄
    desc_html = (
        f'<div class="description-section"><h2>📝 概要欄 / Description</h2>'
        f'<div class="description-content">{esc(r["description"])}</div></div>'
    ) if r.get("description") else ""

    # 字幕
    subs = r.get("subtitles", {})
    if subs:
        tabs   = "".join(f'<button class="lang-tab" data-lang="{esc(l)}" onclick="showLang(\'{esc(l)}\')">{esc(l.upper())}</button>' for l in subs)
        panels = "".join(f'<div class="lang-panel" id="lang-{esc(l)}" style="display:none"><div class="subtitle-content">{esc(t)}</div></div>' for l,t in subs.items())
        sub_html = (
            f'<div class="subtitle-section"><h2>💬 字幕 / Subtitles</h2>'
            f'<div class="subtitle-lang-tabs">{tabs}</div>{panels}</div>'
        )
    else:
        sub_html = ""

    return f"""<!DOCTYPE html>
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
      {thumb}
      <div class="recipe-hero-body">
        <h1>{title}</h1>
        <div class="recipe-meta">
          <span>📺 {esc(r["channel"])}</span>{dur}
          <span>📅 {esc(r["added_at"])}</span>
        </div>
        <div class="recipe-source">
          <a href="{esc(r["url"])}" target="_blank" rel="noopener">▶ 元動画を見る</a>
        </div>
      </div>
    </div>
    <div class="recipe-sections">{ing_html}{step_html}</div>
    {desc_html}
    {sub_html}
  </div>
  <script>
    function showLang(lang) {{
      document.querySelectorAll(".lang-panel").forEach(p => p.style.display = "none");
      document.querySelectorAll(".lang-tab").forEach(t => t.classList.remove("active"));
      const p = document.getElementById("lang-" + lang);
      if (p) p.style.display = "block";
      const t = document.querySelector('.lang-tab[data-lang="' + lang + '"]');
      if (t) t.classList.add("active");
    }}
    const first = document.querySelector(".lang-tab");
    if (first) showLang(first.dataset.lang);
  </script>
</body>
</html>"""

# ── index.html 再生成 ────────────────────────────────────
def rebuild_index(index):
    recipes_js = json.dumps(index, ensure_ascii=False, indent=2)
    html = (
        '<!DOCTYPE html>\n<html lang="ja">\n<head>\n'
        '  <meta charset="UTF-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '  <title>My Recipe Book</title>\n'
        '  <link rel="stylesheet" href="assets/style.css">\n'
        '</head>\n<body>\n'
        '  <header class="site-header">\n'
        '    <h1>\U0001f373 My Recipe Book</h1>\n'
        '    <p>\u52d5\u753b\u304b\u3089\u96c6\u3081\u305f\u30ec\u30b7\u30d4\u30b3\u30ec\u30af\u30b7\u30e7\u30f3</p>\n'
        '    <div class="search-bar">\n'
        '      <input type="text" id="search" placeholder="\u30ec\u30b7\u30d4\u3092\u691c\u7d22... / Search recipes...">\n'
        '    </div>\n  </header>\n'
        '  <main class="main-content">\n'
        '    <p class="section-title">\u30ec\u30b7\u30d4\u4e00\u89a7 <span id="recipe-count"></span></p>\n'
        '    <div class="recipe-grid" id="recipe-grid"></div>\n'
        '    <div class="empty-state" id="empty-state" style="display:none">\n'
        '      <div class="icon">\U0001f4ed</div>\n'
        '      <p>\u30ec\u30b7\u30d4\u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093</p>\n'
        '    </div>\n  </main>\n'
        '  <script>\n'
        '    const allRecipes = ' + recipes_js + ';\n'
        '    function esc(s){return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}\n'
        '    function renderGrid(recipes){\n'
        '      const grid=document.getElementById("recipe-grid"),empty=document.getElementById("empty-state");\n'
        '      document.getElementById("recipe-count").textContent="("+allRecipes.length+")";\n'
        '      if(!recipes.length){grid.innerHTML="";empty.style.display="block";return;}\n'
        '      empty.style.display="none";\n'
        '      grid.innerHTML=recipes.map(function(r){\n'
        '        var th=r.thumbnail?"<img src=\\""+r.thumbnail+"\\" alt=\\""+esc(r.title)+"\\" loading=\\"lazy\\" onerror=\\"this.style.display=\'none\'\\">":"";\n'
        '        var dur=r.duration?"<span>\u23f1 "+r.duration+"</span>":"";\n'
        '        var tags=(r.tags||[]).slice(0,4).map(function(t){return"<span class=\'tag\'>"+esc(t)+"</span>";}).join("");\n'
        '        return"<a class=\'recipe-card\' href=\'recipes/"+r.id+".html\'>"+th\n'
        '          +"<div class=\'card-body\'><div class=\'card-title\'>"+esc(r.title)+"</div>"\n'
        '          +"<div class=\'card-meta\'><span>\U0001f4fa "+esc(r.channel||"")+"</span>"+dur+"<span>\U0001f4c5 "+(r.added_at||"")+"</span></div>"\n'
        '          +"<div class=\'card-tags\'>"+tags+"</div></div></a>";\n'
        '      }).join("");\n'
        '    }\n'
        '    document.getElementById("search").addEventListener("input",function(e){\n'
        '      var q=e.target.value.toLowerCase();\n'
        '      renderGrid(allRecipes.filter(function(r){\n'
        '        return r.title.toLowerCase().includes(q)||(r.channel||"").toLowerCase().includes(q)||(r.tags||[]).some(function(t){return t.toLowerCase().includes(q);});\n'
        '      }));\n'
        '    });\n'
        '    renderGrid(allRecipes);\n'
        '  </script>\n</body>\n</html>\n'
    )
    with open(os.path.join(PROJECT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)

# ── メイン ───────────────────────────────────────────────
def save_recipe(recipe):
    vid = recipe["id"]

    with open(os.path.join(RECIPES_DIR, f"{vid}.json"), "w", encoding="utf-8") as f:
        json.dump(recipe, f, ensure_ascii=False, indent=2)

    with open(os.path.join(RECIPES_DIR, f"{vid}.html"), "w", encoding="utf-8") as f:
        f.write(build_html(recipe))

    index_path = os.path.join(RECIPES_DIR, "recipes.json")
    with open(index_path, encoding="utf-8") as f:
        index = json.load(f)
    entry = {k: recipe[k] for k in ("id","title","channel","thumbnail","duration","added_at","tags","url")}
    ids = [r["id"] for r in index]
    if vid in ids:
        index = [entry if r["id"] == vid else r for r in index]
    else:
        index.insert(0, entry)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    rebuild_index(index)
    print(f"保存完了: {recipe['title']}")


if __name__ == "__main__":
    info_path = os.path.join(PROJECT_DIR, "video_info.json")
    with open(info_path, encoding="utf-8") as f:
        info = json.load(f)

    vid = info["id"]
    subs = load_subtitles(vid)

    recipe = {
        "id": vid,
        "title": info.get("title", ""),
        "channel": info.get("uploader", "") or info.get("channel", ""),
        "url": info.get("webpage_url", ""),
        "thumbnail": info.get("thumbnail", ""),
        "duration": format_duration(info.get("duration")),
        "upload_date": info.get("upload_date", ""),
        "added_at": datetime.now().strftime("%Y-%m-%d"),
        "tags": (info.get("tags") or [])[:10],
        "description": info.get("description", "") or "",
        "ingredients": [],
        "steps": [],
        "subtitles": subs,
    }
    save_recipe(recipe)
