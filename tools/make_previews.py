"""从整屏截图里裁出「仅应用内容区」的图片，用于 README。

要求：不含桌面、任务栏、左侧边栏（项目 / 对话 / 账号），不含输入框里的项目名。
裁剪后放大 2 倍便于阅读。
"""
from pathlib import Path

from PIL import Image

ATT = Path(r"C:\Users\Admin（无密码）\.dsh\attachments\v1\objects")
OUT = Path(r"D:\agent-project\dsh-project\test-4\agy-zh\docs")

JOBS = [
    # (源图相对路径, 裁剪框 x1,y1,x2,y2, 输出名)
    ("33/3390c9af4ca800e6ac6f2cf74adc2be8b521cc571c37597cc96de15a2ca619fc", (458, 86, 1044, 656), "preview-settings-general.png"),
    ("8a/8ab887257a41168e941b6c29fad90f65a8cf064e1e34ef189294d4b9a2cd17fa", (462, 500, 1040, 645), "preview-settings-card.png"),
    ("be/be49b4670408b95b0aaff0200c4c7c40929789d3c23bf0894e17c7680e90a226", (190, 55, 1360, 682), "preview-marketplace.png"),
    ("25/257b9522dabec6cb768895a7754075fd45151c6f327a01d81b2b77adfc269f5b", (524, 473, 698, 688), "preview-models.png"),
]

for rel, box, name in JOBS:
    src = ATT / rel
    img = Image.open(src)
    print(f"{name}: source {img.size}")
    crop = img.crop(box)
    crop = crop.resize((crop.width * 2, crop.height * 2), Image.LANCZOS)
    crop = crop.convert("RGB")
    dst = OUT / name
    crop.save(dst, quality=92)
    print(f"  -> {dst}  {crop.size}")
