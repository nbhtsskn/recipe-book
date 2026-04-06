"""
push_recipe.py — レシピをGitHubにpushして一時ファイルを削除する
Usage: python push_recipe.py
"""
import subprocess, os, shutil, json, sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

def run(cmd):
    result = subprocess.run(cmd, shell=True, cwd=PROJECT_DIR, capture_output=True, text=True, encoding="utf-8")
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0 and result.stderr.strip():
        print("[ERROR]", result.stderr.strip())
    return result.returncode

def get_latest_recipe_title():
    try:
        with open(os.path.join(PROJECT_DIR, "recipes", "recipes.json"), encoding="utf-8") as f:
            index = json.load(f)
        return index[0]["title"][:60] if index else "recipe"
    except:
        return "recipe"

def cleanup():
    targets = ["video_info.json", "video_meta.json"]
    for t in targets:
        p = os.path.join(PROJECT_DIR, t)
        if os.path.exists(p):
            os.remove(p)
            print(f"  削除: {t}")
    sub = os.path.join(PROJECT_DIR, "subtitles")
    if os.path.isdir(sub):
        shutil.rmtree(sub)
        print("  削除: subtitles/")

def main():
    title = get_latest_recipe_title()
    commit_msg = f"Add recipe: {title}"

    print("[1/3] ファイルをステージング...")
    run("git add recipes/ index.html")

    print("[2/3] コミット & push...")
    run(f'git commit -m "{commit_msg}"')
    code = run("git push")
    if code != 0:
        print("push失敗。中断します。")
        sys.exit(1)

    print("[3/3] 一時ファイルを削除...")
    cleanup()

    print(f"\n完了！ https://nbhtsskn.github.io/recipe-book/")

if __name__ == "__main__":
    main()
