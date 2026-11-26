"""列出收集到的长句英文（多为扩展市场里的 app 描述），供批量补译。"""
import json
import os
import re
from pathlib import Path

MISS = Path(os.environ["APPDATA"]) / "Antigravity" / "agy-zh" / "missing.jsonl"
DICT = Path(r"D:\agent-project\dsh-project\test-4\agy-zh\assets\dict.json")
OVR = Path(r"D:\agent-project\dsh-project\test-4\agy-zh\assets\overrides.json")

known = set(json.loads(DICT.read_text(encoding="utf-8")).keys())
if OVR.exists():
    known |= set(json.loads(OVR.read_text(encoding="utf-8")).keys())
known_lower = {k.lower() for k in known}

seen = set()
rows = []
for line in MISS.read_text(encoding="utf-8", errors="ignore").splitlines():
    line = line.strip()
    if not line:
        continue
    t = json.loads(line).get("t", "").strip()
    if not t or t in seen:
        continue
    seen.add(t)
    if t in known or t.lower() in known_lower:
        continue
    if re.search(r"[\u3400-\u9fff]", t):
        continue
    if not re.search(r"[A-Za-z]{2}", t):
        continue
    rows.append(t)

long_rows = [t for t in rows if len(t) >= 40]
print(f"collected-unique: {len(seen)}  unknown: {len(rows)}  long(>=40): {len(long_rows)}\n")
for t in sorted(long_rows, key=len, reverse=True):
    print("---")
    print(t)
