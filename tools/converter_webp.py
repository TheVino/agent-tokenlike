"""Converte WebP (OpenPets) em PNG RGBA ao lado do original: python tools/converter_webp.py <pasta ou .webp>"""
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Falta o Pillow: pip install pillow")

alvo = Path(sys.argv[1]) if len(sys.argv) > 1 else sys.exit(__doc__)
webps = [alvo] if alvo.is_file() else sorted(alvo.glob("*.webp"))
if not webps:
    sys.exit(f"Nenhum .webp em {alvo}")
for w in webps:
    png = w.with_suffix(".png")
    Image.open(w).convert("RGBA").save(png)
    print(png)
