import yt_dlp
import pysrt
from googletrans import Translator
import os
import time
import subprocess

# -------------------------
video_url = input("Enter video URL: ")

# Priority order: prefer Chinese subs, fall back to English
LANG_PRIORITY = [
    ("zh-cn", ["zh-CN", "zh", "zh-Hans", "zh-Hant", "zh-HK", "zh-TW"]),
    ("en", ["en", "en-US", "en-GB"])
]

# Build the list of subtitle language codes yt-dlp should try to fetch
lang_targets = []
for _, aliases in LANG_PRIORITY:
    for alias in aliases:
        if alias not in lang_targets:
            lang_targets.append(alias)
lang_translate = "km"  # Khmer
# -------------------------

# 1️⃣ Download video + subtitles
ydl_opts = {
    "format": "bestvideo+bestaudio/best",
    "writesubtitles": True,
    "subtitleslangs": lang_targets,
    "subtitlesformat": "srt",
    "outtmpl": "%(title)s.%(ext)s"
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(video_url, download=True)
    video_filename = ydl.prepare_filename(info)
    video_title = info.get("title", "video")

# 2️⃣ Find downloaded subtitle file
def match_subtitle_file(filename: str):
    lower_name = filename.lower()
    if not lower_name.endswith(".srt"):
        return None
    for canonical, aliases in LANG_PRIORITY:
        for alias in aliases:
            alias_lower = alias.lower()
            alias_token = f".{alias_lower}."
            alias_suffix = f"_{alias_lower}.srt"
            alias_end = f".{alias_lower}.srt"
            if alias_token in lower_name or lower_name.endswith(alias_suffix) or lower_name.endswith(alias_end):
                return canonical
    return None


srt_file = None
found_lang = None

for f in os.listdir("."):
    matched_lang = match_subtitle_file(f)
    if matched_lang:
        # ensure we keep whichever language has higher priority
        if not found_lang:
            srt_file = f
            found_lang = matched_lang
        else:
            current_priority = next(
                (idx for idx, (lang, _) in enumerate(LANG_PRIORITY) if lang == found_lang),
                float("inf")
            )
            new_priority = next(
                (idx for idx, (lang, _) in enumerate(LANG_PRIORITY) if lang == matched_lang),
                float("inf")
            )
            if new_priority < current_priority:
                srt_file = f
                found_lang = matched_lang

if srt_file:
    print(f"Found subtitle language: {found_lang} ({srt_file})")

if not srt_file:
    print("No Chinese or English subtitles found!")
    exit()

# 3️⃣ Translate subtitles
subs = pysrt.open(srt_file, encoding='utf-8')
translator = Translator()

for item in subs:
    try:
        text = item.text.strip()
        if len(text) > 200:
            parts = [text[i:i+200] for i in range(0, len(text), 200)]
            translated_parts = []
            for part in parts:
                translated_parts.append(translator.translate(
                    part, src=found_lang, dest=lang_translate).text)
                time.sleep(0.1)
            item.text = " ".join(translated_parts)
        else:
            item.text = translator.translate(
                text, src=found_lang, dest=lang_translate).text
    except Exception as e:
        print("Error translating:", e)
        item.text = "[Translation Error]"

kh_srt_file = f"{video_title}_kh.srt"
subs.save(kh_srt_file, encoding='utf-8')
print(f"Khmer subtitle saved as: {kh_srt_file}")

# 4️⃣ Burn subtitles into video using ffmpeg
output_video = f"{video_title}_kh.mp4"
ffmpeg_cmd = [
    "ffmpeg",
    "-i", video_filename,
    "-vf", f"subtitles={kh_srt_file}",
    "-c:a", "copy",
    output_video
]

print("Burning subtitles into video...")
subprocess.run(ffmpeg_cmd)
print(f"Done! Video with Khmer subtitles: {output_video}")
