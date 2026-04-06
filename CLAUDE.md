# Recipe Book — Claude への指示

## ユーザーがYouTube URLを送ってきたときの手順

以下の手順を必ず順番通りに実行すること。

### Step 1: 動画情報を取得

```bash
cd c:/Users/sasak/project
yt-dlp --dump-json --skip-download "<URL>" > video_info.json
```

### Step 2: メタ情報を確認

```bash
python -c "
import json
with open('c:/Users/sasak/project/video_info.json','r',encoding='utf-8') as f:
    d=json.load(f)
with open('c:/Users/sasak/project/video_meta.json','w',encoding='utf-8') as f:
    json.dump({'title':d.get('title',''),'channel':d.get('uploader',''),'duration':d.get('duration',''),'thumbnail':d.get('thumbnail',''),'upload_date':d.get('upload_date',''),'description':d.get('description','')[:5000]},f,ensure_ascii=False,indent=2)
"
```

その後 video_meta.json を Read ツールで読む。

### Step 3: 字幕を取得

```bash
mkdir -p c:/Users/sasak/project/subtitles
yt-dlp --skip-download --write-auto-subs --sub-format vtt --sub-langs "ja,en,zh,ko" \
  -o "c:/Users/sasak/project/subtitles/%(id)s.%(ext)s" "<URL>"
```

取得できた字幕ファイルを Read ツールで読む（日本語優先、なければ英語）。

### Step 4: レシピを分析してJSONを作成

概要欄と字幕を分析し、以下の完全なスキーマでJSONを作成する。

**必須フィールド：**

```json
{
  "id": "動画ID（URLのv=以降）",
  "title": "動画タイトル（原語のまま）",
  "channel": "チャンネル名",
  "url": "https://www.youtube.com/watch?v=動画ID",
  "thumbnail": "サムネイルURL（video_info.jsonから取得）",
  "duration": "M:SS または H:MM:SS",
  "upload_date": "YYYY-MM-DD",
  "added_at": "今日の日付 YYYY-MM-DD",
  "tags": ["タグ1", "タグ2"],
  "description": "概要欄の全文",
  "ingredients": [
    {"name": "材料名", "amount": "分量"}
  ],
  "steps": [
    {
      "step": 1,
      "text": "手順の説明（簡潔に1〜2文）",
      "point": "この手順のポイント・理由・コツを2〜4文で詳しく説明"
    }
  ],
  "subtitles": {
    "ja": "日本語字幕テキスト",
    "en": "英語字幕テキスト"
  }
}
```

**分析のルール：**

- `ingredients`: 概要欄に材料一覧があればそこから抽出。なければ字幕から推測。
- `steps.text`: 何をするかを簡潔に。料理の動作として書く。
- `steps.point`: なぜそうするのか、どんな効果があるのか、失敗しないコツを具体的に書く。動画内で強調されていた情報を優先する。字幕から読み取れる料理人のこだわりや理由を含める。
- 言語は動画の言語に関係なく、`steps.text` と `steps.point` は**日本語で書く**。
- `tags` は料理名・調理法・食材・チャンネル名などを5〜8個。

### Step 5: JSONをファイルに書き込む

`c:/Users/sasak/project/recipes/<動画ID>.json` に Write ツールで保存。

### Step 6: HTMLとindexを生成

```bash
python c:/Users/sasak/project/make_recipe.py
```

※ make_recipe.py はvideo_info.jsonとsubtitlesを読んでJSONのベースを作るが、
  ingredientsとstepsはStep5で保存したJSONから上書きされないため、
  Step5でJSONを保存した後に以下のスクリプトを実行すること：

```bash
python -c "
import json, sys
sys.path.insert(0,'c:/Users/sasak/project')
from make_recipe import save_recipe
with open('c:/Users/sasak/project/recipes/<動画ID>.json',encoding='utf-8') as f:
    r=json.load(f)
save_recipe(r)
"
```

### Step 7: pushして一時ファイルを削除

```bash
python c:/Users/sasak/project/push_recipe.py
```

---

## ファイル構成（変更禁止）

```
project/
├── CLAUDE.md                  ← この指示ファイル
├── index.html                 ← 自動生成（make_recipe.pyが更新）
├── assets/
│   └── style.css              ← デザイン（変更する場合はユーザーに確認）
├── recipes/
│   ├── recipes.json           ← 全レシピのインデックス（自動更新）
│   ├── <video_id>.json        ← レシピデータ
│   └── <video_id>.html        ← レシピページ（自動生成）
├── make_recipe.py             ← HTML・index生成スクリプト
└── push_recipe.py             ← git push + 一時ファイル削除スクリプト
```

一時ファイル（push後に自動削除）:
- `video_info.json`
- `video_meta.json`
- `subtitles/`

## サイトURL

https://nbhtsskn.github.io/recipe-book/
