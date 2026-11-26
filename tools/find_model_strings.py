"""在 language_server.exe 里搜索模型说明文案，提取上下文里的可打印字符串。"""
import re
from pathlib import Path

BIN = Path(r"C:\Users\Admin（无密码）\AppData\Local\Programs\antigravity\resources\bin\language_server.exe")
NEEDLES = [b"hardest, long-horizon", b"Leaving on", b"The original Gemini 4 model", b"quota usage"]

data = BIN.read_bytes()
print("size MB:", round(len(data) / 1024 / 1024, 1))

hits = []
for needle in NEEDLES:
    start = 0
    while True:
        idx = data.find(needle, start)
        if idx < 0:
            break
        hits.append((needle.decode(), idx))
        start = idx + 1
        if len(hits) > 60:
            break

print("hits:", len(hits))
for name, idx in hits[:10]:
    print(f"  {name} @ {idx:#x}")

if hits:
    idx = hits[0][1]
    window = data[max(0, idx - 4000): idx + 4000]
    # 提取长度 >= 12 的可打印 ASCII 片段
    strings = re.findall(rb"[\x20-\x7e]{12,}", window)
    seen = set()
    print("\n--- nearby strings ---")
    for s in strings:
        t = s.decode("ascii", "ignore").strip()
        if t in seen:
            continue
        seen.add(t)
        print(t)
