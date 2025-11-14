import pysrt
from googletrans import Translator

translator = Translator()

input_file = "input.srt"
output_file = "output_kh.srt"

subs = pysrt.open(input_file, encoding='utf-8')

for item in subs:
    try:
        # Translate Chinese text to Khmer
        translated = translator.translate(item.text, src='zh-cn', dest='km')
        item.text = translated.text
    except Exception as e:
        print("Error:", e)

subs.save(output_file, encoding='utf-8')
print("Done! Saved:", output_file)
