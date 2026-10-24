"""Hojas de contacto para revision manual. Uso: python3 -I contact_sheet.py <dir_imgs> <out_prefix> [cols rows tile]"""
import sys, os, site, warnings
warnings.filterwarnings("ignore")
sys.path.append(site.getusersitepackages())
from PIL import Image, ImageDraw, ImageFont, ImageOps

src, outp = sys.argv[1], sys.argv[2]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else 5
rows = int(sys.argv[4]) if len(sys.argv) > 4 else 4
tile = int(sys.argv[5]) if len(sys.argv) > 5 else 300
files = sorted(f for f in os.listdir(src) if f.lower().endswith((".jpg", ".jpeg", ".png")))
per = cols * rows
try:
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22)
except Exception:
    font = ImageFont.load_default()
idx = []
for sheet in range((len(files) + per - 1) // per):
    canvas = Image.new("RGB", (cols * tile, rows * tile), "white")
    dr = ImageDraw.Draw(canvas)
    for k, fn in enumerate(files[sheet * per:(sheet + 1) * per]):
        i = sheet * per + k
        try:
            im = Image.open(os.path.join(src, fn))
            im = ImageOps.exif_transpose(im).convert("RGB")
            im.thumbnail((tile - 6, tile - 6))
        except Exception as e:
            im = Image.new("RGB", (tile - 6, tile - 6), "red")
        x, y = (k % cols) * tile, (k // cols) * tile
        canvas.paste(im, (x + 3, y + 3))
        dr.rectangle([x + 3, y + 3, x + 50, y + 30], fill="black")
        dr.text((x + 6, y + 5), str(i), fill="yellow", font=font)
        idx.append("%d\t%s" % (i, fn))
    canvas.save("%s_%02d.jpg" % (outp, sheet), quality=85)
open(outp + "_index.tsv", "w").write("\n".join(idx) + "\n")
print(len(files), "imgs ->", (len(files) + per - 1) // per, "hojas")
