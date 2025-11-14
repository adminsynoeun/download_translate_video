import yt_dlp
import pysrt
from googletrans import Translator
import os
import time

# -------------------------
video_url = input("Enter video URL: ")
lang_targets = ["zh-cn", "en"]  # Check Chinese first, then English
lang_translate = "km"            # Khmer
output_srt = "subtitle_kh.srt"
# -------------------------

# 1️⃣ Download subtitles only
ydl_opts = {
    "skip_download": True,
    "writesubtitles": True,
    "subtitleslangs": lang_targets,
    "subtitleformat": "srt",
    "outtmpl": "temp_video.%(ext)s"
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(video_url, download=True)

# 2️⃣ Find downloaded subtitle file
srt_file = None
found_lang = None
for lang in lang_targets:
    for f in os.listdir('.'):
        if f.endswith(".srt") and lang in f:
            srt_file = f
            found_lang = lang
            print(f"Found subtitle language: {lang}")
            break
    if srt_file:
        break

if not srt_file:
    print("No Chinese or English subtitles found!")
    exit()

# 3️⃣ Translate subtitles
subs = pysrt.open(srt_file, encoding='utf-8')
translator = Translator()

for item in subs:
    try:
        # Google Translate API sometimes fails on long text
        # Split into shorter chunks if needed
        text = item.text.strip()
        if len(text) > 200:  # arbitrary chunk size
            parts = [text[i:i+200] for i in range(0, len(text), 200)]
            translated_parts = []
            for part in parts:
                translated_parts.append(translator.translate(part, src=found_lang, dest=lang_translate).text)
                time.sleep(0.1)  # avoid hitting API limits
            item.text = " ".join(translated_parts)
        else:
            item.text = translator.translate(text, src=found_lang, dest=lang_translate).text
    except Exception as e:
        print("Error translating:", e)
        item.text = "[Translation Error]"

# 4️⃣ Save Khmer subtitle
subs.save(output_srt, encoding='utf-8')
print(f"Done! Khmer subtitle saved as: {output_srt}")
