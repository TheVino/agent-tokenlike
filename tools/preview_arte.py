"""Gera preview_arte.png com todos os desenhos do arte.py (precisa do Pillow: pip install pillow)."""
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import arte
from PIL import Image, ImageDraw
arte.validate()
def to_img(g,pal,s):
    w,h=len(g[0]),len(g); im=Image.new("RGBA",(w*s,h*s),(0,0,0,0)); d=ImageDraw.Draw(im)
    for y,r in enumerate(g):
        for x,ch in enumerate(r):
            c=pal.get(ch)
            if c: d.rectangle([x*s,y*s,x*s+s-1,y*s+s-1],fill=c)
    return im
art=arte.all_art(); s=7
sheet=Image.new("RGBA",(8*110,4*100),(200,200,210,255)); d=ImageDraw.Draw(sheet)
for i,(k,g) in enumerate(art.items()):
    x,y=(i%8)*110+10,(i//8)*100+8
    sheet.alpha_composite(to_img(g,arte.PAL,s),(x,y)); d.text((x,y+80),k,fill=(0,0,0))
sheet.save(Path(__file__).resolve().parent / "preview_arte.png"); print(len(art))
