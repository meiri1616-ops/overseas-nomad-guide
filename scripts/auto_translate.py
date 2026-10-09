import os
import re
import glob
import time
import requests

TARGET_LANGS = {
    "zh-TW": {
        "filename": "README_zh-TW.md",
        "folder": "zh-TW",
        "name": "繁體中文",
        "current_label": "🇭🇰/🇹🇼 繁體中文 (目前)",
        "prompt": "Translate this Markdown document into Traditional Chinese (Taiwan/Hong Kong convention). Use local terms: 網路 instead of 网络, 伺服器 instead of 服务器, 聯盟行銷 instead of 联盟营销, 分潤 instead of 分成, 提現/出金 instead of 提现."
    },
    "en": {
        "filename": "README_en.md",
        "folder": "en",
        "name": "English",
        "current_label": "🇺🇸 English (Current)",
        "prompt": "Translate this Markdown document into fluent, professional English tailored for indie hackers, software engineers, and affiliate marketers. Emphasize terms like 'Recurring Commission', 'DevTools', 'Indie Hacker', and 'Payout Rails'."
    },
    "ja": {
        "filename": "README_ja.md",
        "folder": "ja",
        "name": "日本語",
        "current_label": "🇯🇵 日本語 (現在)",
        "prompt": "Translate this Markdown document into natural Japanese tailored for software developers and tech entrepreneurs (e.g., アフィリエイト, 継続報酬, 不労所得, SaaS, 個人開発)."
    },
    "de": {
        "filename": "README_de.md",
        "folder": "de",
        "name": "Deutsch",
        "current_label": "🇩🇪 Deutsch (Aktuell)",
        "prompt": "Translate this Markdown document into precise, professional German, emphasizing B2B SaaS, recurring commissions (Wiederkehrende Provisionen), and tax compliance (W-8BEN)."
    },
    "es": {
        "filename": "README_es.md",
        "folder": "es",
        "name": "Español",
        "current_label": "🇪🇸 Español (Actual)",
        "prompt": "Translate this Markdown document into neutral, professional Spanish (Español neutro) suitable for Latin America and Spain, focusing on digital nomads and indie developers."
    }
}

def build_lang_bar(current_code):
    links = [
        "[ 🇨🇳 简体中文 ](./README.md)" if current_code != "zh-CN" else "[ 🇨🇳 简体中文 (当前) ](./README.md)",
        "[ 🇭🇰/🇹🇼 繁體中文 ](./README_zh-TW.md)" if current_code != "zh-TW" else "[ 🇭🇰/🇹🇼 繁體中文 (目前) ](./README_zh-TW.md)",
        "[ 🇺🇸 English ](./README_en.md)" if current_code != "en" else "[ 🇺🇸 English (Current) ](./README_en.md)",
        "[ 🇯🇵 日本語 ](./README_ja.md)" if current_code != "ja" else "[ 🇯🇵 日本語 (現在) ](./README_ja.md)",
        "[ 🇩🇪 Deutsch ](./README_de.md)" if current_code != "de" else "[ 🇩🇪 Deutsch (Aktuell) ](./README_de.md)",
        "[ 🇪🇸 Español ](./README_es.md)" if current_code != "es" else "[ 🇪🇸 Español (Actual) ](./README_es.md)"
    ]
    return f"<!-- 多语言切换栏 -->\n**Language / 语言切换**:\n" + " · ".join(links)

def translate_with_gemini(text, target_conf):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise Exception("未检测到 GEMINI_API_KEY")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    system_instruction = (
        f"{target_conf['prompt']}\n"
        "CRITICAL RULES:\n"
        "1. Do NOT translate or modify any URLs, affiliate links, image links, or badges.\n"
        "2. Keep the exact Markdown table structure, pipes '|', and spacing.\n"
        "3. Keep code blocks, backticks `...`, and tags untouched.\n"
        "4. Output ONLY the translated Markdown directly, with NO conversational filler."
    )

    payload = {
        "contents": [{"parts": [
            {"text": system_instruction},
            {"text": text}
        ]}],
        "generationConfig": {"temperature": 0.2}
    }

    res = requests.post(url, json=payload, headers=headers, timeout=60)
    if res.status_code == 200:
        data = res.json()
        candidates = data.get("candidates", [])
        if candidates:
            return candidates[0]["content"]["parts"][0]["text"].strip()
    
    raise Exception(f"Gemini 翻译失败 (HTTP {res.status_code}): {res.text}")

def main():
    if not os.path.exists("README.md"):
        print("未找到 README.md，退出。")
        return

    with open("README.md", "r", encoding="utf-8") as f:
        readme_content = f.read()

    readme_clean = re.sub(r"<!-- 多语言切换栏 -->.*?\*\*Language / 语言切换\*\*.*?(?=\n\n|\r\n\r\n)", "", readme_content, flags=re.DOTALL)

    # 扫描 docs 目录下所有中文主章节（排除语言子目录）
    doc_files = [f for f in glob.glob("docs/*.md") if not any(lang in f for lang in TARGET_LANGS.keys())]

    for lang_code, conf in TARGET_LANGS.items():
        print(f"\n🌍 ================= 正在处理语言：{conf['name']} ({lang_code}) =================")
        
        # 1. 翻译主页 README
        try:
            print(f"⏳ 正在生成主页 {conf['filename']}...")
            translated_readme = translate_with_gemini(readme_clean, conf)
            
            # 自动把主页里的 ./docs/ 链接无缝替换为对应语言子目录 ./docs/{lang_code}/
            translated_readme = translated_readme.replace("(./docs/", f"(./docs/{conf['folder']}/)")
            
            lang_bar = build_lang_bar(lang_code)
            if "# 🛠️" in translated_readme:
                parts = translated_readme.split("# 🛠️", 1)
                final_readme = parts[0] + "# 🛠️" + parts[1].split("\n", 1)[0] + f"\n\n{lang_bar}\n" + parts[1].split("\n", 1)[1]
            else:
                final_readme = f"{lang_bar}\n\n" + translated_readme

            with open(conf["filename"], "w", encoding="utf-8") as out_f:
                out_f.write(final_readme)
            print(f"✅ {conf['filename']} 主页生成完毕！")
        except Exception as e:
            print(f"❌ 翻译 {conf['filename']} 出错: {e}")

        time.sleep(2)  # 防限频休眠

        # 2. 递归翻译 docs 目录下的所有子章节
        target_doc_dir = f"docs/{conf['folder']}"
        os.makedirs(target_doc_dir, exist_ok=True)

        for doc_path in doc_files:
            file_name = os.path.basename(doc_path)
            target_file_path = os.path.join(target_doc_dir, file_name)
            
            print(f"⏳ 正在递归翻译子章节：{doc_path} -> {target_file_path} ...")
            try:
                with open(doc_path, "r", encoding="utf-8") as df:
                    doc_text = df.read()
                
                translated_doc = translate_with_gemini(doc_text, conf)
                
                # 在子章节顶部加入返回首页导航条
                home_link = f"../../{conf['filename']}"
                nav_header = f"[ ⬅️ 返回手册首页 (Home) ]({home_link})\n\n---\n\n"
                
                with open(target_file_path, "w", encoding="utf-8") as tf:
                    tf.write(nav_header + translated_doc)
                    
                print(f"✅ {target_file_path} 章节翻译完成！")
            except Exception as e:
                print(f"❌ 翻译子章节 {doc_path} 出错: {e}")

            time.sleep(2)  # 防限频休眠

if __name__ == "__main__":
    main()
