"""Generates preview_art.png with every drawing from art.py (needs Pillow: pip install pillow)."""
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import art
from PIL import Image, ImageDraw
art.validate()
def to_img(g,pal,s):
    w,h=len(g[0]),len(g); im=Image.new("RGBA",(w*s,h*s),(0,0,0,0)); d=ImageDraw.Draw(im)
    for y,r in enumerate(g):
        for x,ch in enumerate(r):
            c=pal.get(ch)
            if c: d.rectangle([x*s,y*s,x*s+s-1,y*s+s-1],fill=c)
    return im
arts=art.all_art(); s=7
sheet=Image.new("RGBA",(8*110,-(-len(arts)//8)*100),(200,200,210,255)); d=ImageDraw.Draw(sheet)
for i,(k,g) in enumerate(arts.items()):
    x,y=(i%8)*110+10,(i//8)*100+8
    sheet.alpha_composite(to_img(g,art.PAL,s),(x,y)); d.text((x,y+80),k,fill=(0,0,0))
sheet.save(Path(__file__).resolve().parent / "preview_art.png"); print(len(arts))
