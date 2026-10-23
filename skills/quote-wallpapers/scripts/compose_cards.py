#!/usr/bin/env python3
"""Compose quote lock-screen cards over AI backgrounds. Rotates 3 text treatments."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import os, json, sys

W, H = 1290, 2796
FONTS = {
    "hoefler": "/System/Library/Fonts/Supplemental/Hoefler Text.ttc",
    "iowan":   "/System/Library/Fonts/Supplemental/Iowan Old Style.ttc",
    "didot":   "/System/Library/Fonts/Supplemental/Didot.ttc",
    "futura":  "/System/Library/Fonts/Supplemental/Futura.ttc",
    "basker":  "/System/Library/Fonts/Supplemental/Baskerville.ttc",
}
def font(n, s, i=0): return ImageFont.truetype(FONTS[n], s, index=i)
CREAM = (238, 231, 217)

def _trim_border(img):
    """Detect and crop a bright, low-variance paper frame on any side."""
    import numpy as np
    g = np.asarray(img.convert("L"), dtype=float)
    h, w = g.shape
    def bright(line): return line.mean() > 190 and line.std() < 42
    t = 0
    while t < h*0.14 and bright(g[t]): t += 1
    b = h
    while b > h*0.86 and bright(g[b-1]): b -= 1
    l = 0
    while l < w*0.14 and bright(g[:, l]): l += 1
    r = w
    while r > w*0.86 and bright(g[:, r-1]): r -= 1
    m = 5  # safety margin past the frame
    t = t+m if t else 0; l = l+m if l else 0
    b = b-m if b < h else h; r = r-m if r < w else w
    return img.crop((l, t, r, b))

def cover(img, overscan=1.02):
    img = _trim_border(img)                      # precise cream-frame removal
    r = max(W/img.width, H/img.height) * overscan
    img = img.resize((int(img.width*r)+1, int(img.height*r)+1), Image.LANCZOS)
    x = (img.width-W)//2; y = (img.height-H)//2
    return img.crop((x, y, x+W, y+H)).convert("RGB")

def darken(img, base=0.62):
    img = ImageEnhance.Brightness(img).enhance(base)
    img = ImageEnhance.Color(img).enhance(0.82)
    return img

def scrim(img, top_frac, strength=170):
    ov = Image.new("RGBA", (W, H), (0,0,0,0))
    d = ImageDraw.Draw(ov)
    y0 = int(H*top_frac)
    for y in range(y0, H):
        a = int(strength * min(1,(y-y0)/(H-y0)*1.6))
        d.line([(0,y),(W,y)], fill=(6,7,10,min(a,strength)))
    return Image.alpha_composite(img.convert("RGBA"), ov)

def wrap(d, text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t=(cur+" "+w).strip()
        if d.textlength(t, font=f)<=maxw: cur=t
        else:
            if cur: lines.append(cur)
            cur=w
    if cur: lines.append(cur)
    return lines

def fit(d, text, fn, maxw, maxh, hi, lo, lh, idx=0):
    for s in range(hi, lo, -2):
        f=font(fn,s,idx); L=wrap(d,text,f,maxw)
        a,de=f.getmetrics(); blk=len(L)*int((a+de)*lh)
        if blk<=maxh: return f,L,int((a+de)*lh)
    f=font(fn,lo,idx); return f,wrap(d,text,f,maxw),int(sum(f.getmetrics())*lh)

def draw_c(img,L,f,lh,color,cy,sh=(0,3,(0,0,0,190))):
    d=ImageDraw.Draw(img,"RGBA"); tot=len(L)*lh; y=cy-tot//2
    for ln in L:
        w=d.textlength(ln,font=f); x=(W-w)//2
        d.text((x+sh[0],y+sh[1]),ln,font=f,fill=sh[2]); d.text((x,y),ln,font=f,fill=color); y+=lh
    return y

def tracked(d,t,f,cx,y,color,tr=6):
    tw=sum(d.textlength(c,font=f)+tr for c in t)-tr; x=cx-tw/2
    for c in t: d.text((x,y),c,font=f,fill=color); x+=d.textlength(c,font=f)+tr

def footer_centered(img, author, book, endy, accent=(214,180,120)):
    d=ImageDraw.Draw(img,"RGBA")
    d.line([(W/2-46,endy+42),(W/2+46,endy+42)],fill=accent+(220,),width=2)
    lab=font("futura",30,1); tracked(d,author.upper(),lab,W/2,endy+66,accent,6)
    if book:
        bf=font("hoefler",29,1); bw=d.textlength(book,font=bf)
        d.text(((W-bw)//2,endy+112),book,font=bf,fill=(196,190,178,235))

# ---- styles over an AI background ----
def style_A(bg, q, author, book):           # serif, lower-center
    img=scrim(darken(bg,0.66),0.50,180)
    d=ImageDraw.Draw(img); f,L,lh=fit(d,q,"hoefler",int(W*0.80),int(H*0.34),88,38,1.30)
    endy=draw_c(img,L,f,lh,CREAM,int(H*0.70)); footer_centered(img,author,book,endy)
    return img.convert("RGB")

def style_C(bg, q, author, book):           # didot italic, center
    img=scrim(darken(bg,0.58),0.40,170)
    d=ImageDraw.Draw(img); f,L,lh=fit(d,q,"didot",int(W*0.82),int(H*0.42),98,42,1.32,idx=1)
    endy=draw_c(img,L,f,lh,(242,238,230),int(H*0.55)); footer_centered(img,author,book,endy,(206,176,126))
    return img.convert("RGB")

def _soft_panel(img, box, alpha=135, blur=90):
    """A blurred dark panel behind the text block — legibility without killing color."""
    lay=Image.new("RGBA",(W,H),(0,0,0,0))
    d=ImageDraw.Draw(lay)
    x0,y0,x1,y1=box
    d.rounded_rectangle([x0-70,y0-60,x1+70,y1+60],radius=120,fill=(6,7,10,alpha))
    lay=lay.filter(ImageFilter.GaussianBlur(blur))
    return Image.alpha_composite(img.convert("RGBA"),lay)

def style_B(bg, q, author, book):           # BRUTALIST: sans, left-aligned, vivid art
    author=author or ""; book=book or ""
    img=darken(bg,0.74).convert("RGBA")      # keep color vivid
    mx=int(W*0.12)
    d=ImageDraw.Draw(img,"RGBA")
    f,L,lh=fit(d,q,"futura",int(W*0.78),int(H*0.40),74,32,1.24,idx=1)
    y0=int(H*0.46)
    # measure block for the localized scrim
    bw=max(d.textlength(ln,font=f) for ln in L)
    blk_h=len(L)*lh + 130
    img=_soft_panel(img,(mx,y0-40,mx+bw,y0+blk_h),alpha=140,blur=100)
    d=ImageDraw.Draw(img,"RGBA")
    d.rectangle([mx,y0-46,mx+92,y0-36],fill=(232,84,43,255))   # orange rule
    y=y0
    for ln in L:
        d.text((mx+2,y+3),ln,font=f,fill=(0,0,0,190)); d.text((mx,y),ln,font=f,fill=CREAM); y+=lh
    lab=font("futura",27,0); x=mx
    for c in author.upper(): d.text((x+1,y+29),c,font=lab,fill=(0,0,0,160)); d.text((x,y+28),c,font=lab,fill=(224,224,228,240)); x+=d.textlength(c,font=lab)+5
    if book:
        x=mx
        for c in book.upper(): d.text((x,y+66),c,font=lab,fill=(176,176,184,225)); x+=d.textlength(c,font=lab)+4
    return img.convert("RGB")

STYLES=[style_B]   # brutalist only

def run(render_set, bg_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    bgs=sorted(f for f in os.listdir(bg_dir) if f.lower().endswith(('.png','.jpg')))
    data=json.load(open(render_set))
    for i,item in enumerate(data):
        bg=Image.open(os.path.join(bg_dir,bgs[i%len(bgs)]))
        card=STYLES[i%len(STYLES)](cover(bg), item['display'], item['author'], item.get('book') or "")
        card.save(os.path.join(out_dir,f"lit_{i:03d}.png"))
    print(f"composed {len(data)} cards -> {out_dir}")

if __name__=="__main__":
    run(sys.argv[1], sys.argv[2], sys.argv[3])
