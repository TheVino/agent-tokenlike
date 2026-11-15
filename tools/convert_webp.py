"""Converts WebP (OpenPets) to RGBA PNG next to the original: python tools/convert_webp.py <folder or .webp>"""
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Falta o Pillow: pip install pillow")

target = Path(sys.argv[1]) if len(sys.argv) > 1 else sys.exit(__doc__)
webps = [target] if target.is_file() else sorted(target.glob("*.webp"))
if not webps:
    sys.exit(f"No .webp in {target}")
for w in webps:
    png = w.with_suffix(".png")
    Image.open(w).convert("RGBA").save(png)
    print(png)
