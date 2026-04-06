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
            f'<div class="step-point">{esc(s["point"])}</div>'
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
  </div>
</body>
</html>"""

# ── index.html 再生成 ────────────────────────────────────
def rebuild_index(index):
    recipes_js = json.dumps(index, ensure_ascii=False, indent=2)

    def fmt_num(n):
        if n is None: return ""
        n = int(n)
        if n >= 100000000: return f"{n//100000000}億"
        if n >= 10000: return f"{n//10000}万"
        return f"{n:,}"

    html = '<!DOCTYPE html>\n<html lang="ja">\n<head>\n'
    html += '  <meta charset="UTF-8">\n'
    html += '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
    html += '  <title>My Recipe Book</title>\n'
    html += '  <link rel="stylesheet" href="assets/style.css">\n'
    html += '</head>\n<body>\n'
    html += '  <header class="site-header">\n'
    html += '    <h1>🍳 My Recipe Book</h1>\n'
    html += '    <p>動画から集めたレシピコレクション</p>\n'
    html += '    <div class="search-bar">\n'
    html += '      <input type="text" id="search" placeholder="レシピを検索... / Search recipes...">\n'
    html += '    </div>\n'
    html += '  </header>\n'
    html += '  <main class="main-content">\n'
    html += '    <div class="sort-bar">\n'
    html += '      <span class="sort-label">並び替え：</span>\n'
    html += '      <button class="sort-btn active" data-sort="added_at">追加日</button>\n'
    html += '      <button class="sort-btn" data-sort="view_count">再生回数</button>\n'
    html += '      <button class="sort-btn" data-sort="like_count">いいね数</button>\n'
    html += '      <button class="sort-btn" data-sort="upload_date">投稿日</button>\n'
    html += '      <button class="sort-btn" data-sort="channel">チャンネル</button>\n'
    html += '      <button class="sort-btn" data-sort="duration_seconds">動画時間</button>\n'
    html += '    </div>\n'
    html += '    <p class="section-title">レシピ一覧 <span id="recipe-count"></span></p>\n'
    html += '    <div class="recipe-grid" id="recipe-grid"></div>\n'
    html += '    <div class="empty-state" id="empty-state" style="display:none">\n'
    html += '      <div class="icon">📭</div>\n'
    html += '      <p>レシピが見つかりません</p>\n'
    html += '    </div>\n'
    html += '  </main>\n'
    html += '  <script>\n'
    html += '    const allRecipes = ' + recipes_js + ';\n'
    html += '    var currentSort = "added_at";\n'
    html += '    var currentQuery = "";\n'
    html += '\n'
    html += '    function esc(s){return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");}\n'
    html += '\n'
    html += '    function fmtNum(n){\n'
    html += '      if(n==null) return "";\n'
    html += '      n=parseInt(n);\n'
    html += '      if(n>=100000000) return (n/100000000).toFixed(1)+"億";\n'
    html += '      if(n>=10000) return Math.floor(n/10000)+"万";\n'
    html += '      return n.toLocaleString();\n'
    html += '    }\n'
    html += '\n'
    html += '    function sortRecipes(recipes, key){\n'
    html += '      return recipes.slice().sort(function(a,b){\n'
    html += '        if(key==="channel") return (a.channel||"").localeCompare(b.channel||"","ja");\n'
    html += '        var av=a[key]||0, bv=b[key]||0;\n'
    html += '        if(key==="added_at"||key==="upload_date") return (bv>av?1:bv<av?-1:0);\n'
    html += '        return bv-av;\n'
    html += '      });\n'
    html += '    }\n'
    html += '\n'
    html += '    function getFiltered(){\n'
    html += '      var q=currentQuery;\n'
    html += '      var list=q?allRecipes.filter(function(r){\n'
    html += '        return r.title.toLowerCase().includes(q)||(r.channel||"").toLowerCase().includes(q)||(r.tags||[]).some(function(t){return t.toLowerCase().includes(q);});\n'
    html += '      }):allRecipes;\n'
    html += '      return sortRecipes(list, currentSort);\n'
    html += '    }\n'
    html += '\n'
    html += '    function renderGrid(recipes){\n'
    html += '      var grid=document.getElementById("recipe-grid"),empty=document.getElementById("empty-state");\n'
    html += '      document.getElementById("recipe-count").textContent="("+allRecipes.length+")";\n'
    html += '      if(!recipes.length){grid.innerHTML="";empty.style.display="block";return;}\n'
    html += '      empty.style.display="none";\n'
    html += '      grid.innerHTML=recipes.map(function(r){\n'
    html += '        var th=r.thumbnail?"<img src=\\""+r.thumbnail+"\\" alt=\\""+esc(r.title)+"\\" loading=\\"lazy\\" onerror=\\"this.style.display=\'none\'\\">":"";\n'
    html += '        var meta="<span>📺 "+esc(r.channel||"")+"</span>";\n'
    html += '        if(r.duration) meta+="<span>⏱ "+r.duration+"</span>";\n'
    html += '        if(r.view_count) meta+="<span>▶ "+fmtNum(r.view_count)+"回</span>";\n'
    html += '        if(r.like_count) meta+="<span>👍 "+fmtNum(r.like_count)+"</span>";\n'
    html += '        meta+="<span>📅 "+(r.added_at||"")+"</span>";\n'
    html += '        var tags=(r.tags||[]).slice(0,4).map(function(t){return"<span class=\'tag\'>"+esc(t)+"</span>";}).join("");\n'
    html += '        return"<a class=\'recipe-card\' href=\'recipes/"+r.id+".html\'>"+th\n'
    html += '          +"<div class=\'card-body\'><div class=\'card-title\'>"+esc(r.title)+"</div>"\n'
    html += '          +"<div class=\'card-meta\'>"+meta+"</div>"\n'
    html += '          +"<div class=\'card-tags\'>"+tags+"</div></div></a>";\n'
    html += '      }).join("");\n'
    html += '    }\n'
    html += '\n'
    html += '    document.getElementById("search").addEventListener("input",function(e){\n'
    html += '      currentQuery=e.target.value.toLowerCase();\n'
    html += '      renderGrid(getFiltered());\n'
    html += '    });\n'
    html += '\n'
    html += '    document.querySelectorAll(".sort-btn").forEach(function(btn){\n'
    html += '      btn.addEventListener("click",function(){\n'
    html += '        document.querySelectorAll(".sort-btn").forEach(function(b){b.classList.remove("active");});\n'
    html += '        btn.classList.add("active");\n'
    html += '        currentSort=btn.dataset.sort;\n'
    html += '        renderGrid(getFiltered());\n'
    html += '      });\n'
    html += '    });\n'
    html += '\n'
    html += '    renderGrid(getFiltered());\n'
    html += '  </script>\n</body>\n</html>\n'

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
    entry = {k: recipe.get(k) for k in ("id","title","channel","thumbnail","duration","duration_seconds","added_at","upload_date","tags","url","view_count","like_count")}
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
