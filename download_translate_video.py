import yt_dlp
import pysrt
from googletrans import Translator
import os
import time
import subprocess
import shutil
import glob

# -------------------------
# Create storage folders
STORAGE_FOLDERS = {
    "video": "_video",
    "srt": "srt_file",
    "tmp": "tmp"
}

for folder in STORAGE_FOLDERS.values():
    os.makedirs(folder, exist_ok=True)

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
quality_format = (
    "bestvideo[height>=2160][vcodec!=none]+bestaudio/"
    "bestvideo[height>=1080][vcodec!=none]+bestaudio/"
    "bestvideo+bestaudio/"
    "best"
)

ydl_opts = {
    "format": quality_format,
    "writesubtitles": True,
    "subtitleslangs": lang_targets,
    "subtitlesformat": "srt",
    "outtmpl": os.path.join(STORAGE_FOLDERS["tmp"], "%(title)s.%(ext)s")
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(video_url, download=True)
    video_filename = ydl.prepare_filename(info)
    video_title = info.get("title", "video")
    requested_formats = info.get("requested_formats")
    selected_video = None
    if requested_formats:
        for fmt in requested_formats:
            if fmt.get("vcodec") and fmt.get("vcodec") != "none":
                selected_video = fmt
                break
    if not selected_video:
        selected_video = info
    height = selected_video.get("height")
    fps = selected_video.get("fps")
    print(f"Selected video quality: {height or 'unknown'}p @ {fps or '?'}fps")

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

# Search for subtitle files in tmp folder
tmp_dir = STORAGE_FOLDERS["tmp"]
for f in os.listdir(tmp_dir):
    matched_lang = match_subtitle_file(f)
    if matched_lang:
        # ensure we keep whichever language has higher priority
        if not found_lang:
            srt_file = os.path.join(tmp_dir, f)
            found_lang = matched_lang
        else:
            current_priority = next(
                (idx for idx, (lang, _) in enumerate(
                    LANG_PRIORITY) if lang == found_lang),
                float("inf")
            )
            new_priority = next(
                (idx for idx, (lang, _) in enumerate(
                    LANG_PRIORITY) if lang == matched_lang),
                float("inf")
            )
            if new_priority < current_priority:
                srt_file = os.path.join(tmp_dir, f)
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

# Save Khmer subtitle to srt_file folder
kh_srt_file = os.path.join(STORAGE_FOLDERS["srt"], f"{video_title}_kh.srt")
subs.save(kh_srt_file, encoding='utf-8')
print(f"Khmer subtitle saved as: {kh_srt_file}")

# Move original video file to _video folder
video_basename = os.path.basename(video_filename)
video_dest = os.path.join(STORAGE_FOLDERS["video"], video_basename)
if os.path.exists(video_filename):
    shutil.move(video_filename, video_dest)
    video_filename = video_dest
    print(f"Original video moved to: {video_dest}")

# Move original subtitle file to srt_file folder
srt_basename = os.path.basename(srt_file)
srt_dest = os.path.join(STORAGE_FOLDERS["srt"], srt_basename)
if os.path.exists(srt_file):
    shutil.move(srt_file, srt_dest)
    print(f"Original subtitle moved to: {srt_dest}")

# Move temporary files (*.part, .ytdl) from current directory to tmp folder
for temp_pattern in ["*.part", "*.ytdl"]:
    for temp_file in glob.glob(temp_pattern):
        if os.path.isfile(temp_file):
            temp_dest = os.path.join(STORAGE_FOLDERS["tmp"], temp_file)
            shutil.move(temp_file, temp_dest)
            print(f"Temporary file moved to: {temp_dest}")

# 4️⃣ Burn subtitles into video using ffmpeg
output_video = os.path.join(STORAGE_FOLDERS["video"], f"{video_title}_kh.mp4")
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
