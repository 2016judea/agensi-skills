#!/usr/bin/env python3
"""Verify a press PDF: page count, exact uniform page size, and full-bleed coverage.

Usage: python3 verify_pdf.py <PDF> [--png-dir DIR]

Page geometry is read straight from the PDF /MediaBox (no deps).
If --png-dir is given (the screenshots used to build it), also checks that the
artwork bleeds to the edges (content covers ~0..100%). Coverage ~66% means the
Chrome transform-pagination bug -- you printed instead of screenshotting.
"""
import sys, re, glob, os

def media_boxes(pdf):
    data = open(pdf, "rb").read()
    boxes = re.findall(rb"/MediaBox\s*\[([^\]]+)\]", data)
    sizes = []
    for b in boxes:
        n = [float(x) for x in b.split()]
        sizes.append((round((n[2]-n[0])/72, 4), round((n[3]-n[1])/72, 4)))
    return sizes

def coverage(png):
    from PIL import Image
    im = Image.open(png).convert("RGB"); W, H = im.size; px = im.load()
    def bg(c):
        r, g, b = c
        return r > 245 and g > 245 and b > 245  # near-white only; tighten per design
    minx, miny, maxx, maxy = W, H, 0, 0
    for y in range(0, H, 4):
        for x in range(0, W, 4):
            if not bg(px[x, y]):
                minx, maxx = min(minx, x), max(maxx, x)
                miny, maxy = min(miny, y), max(maxy, y)
    return minx/W, maxx/W, miny/H, maxy/H

def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: verify_pdf.py <PDF> [--png-dir DIR]")
    pdf = sys.argv[1]
    sizes = media_boxes(pdf)
    uniq = sorted(set(sizes))
    print(f"pages: {len(sizes)}")
    for w, h in uniq:
        print(f"  size: {w} x {h} in  ({w*72:.1f} x {h*72:.1f} pt)" +
              ("  <- MULTIPLE SIZES!" if len(uniq) > 1 else ""))
    ok = len(uniq) == 1
    if "--png-dir" in sys.argv:
        d = sys.argv[sys.argv.index("--png-dir") + 1]
        pngs = sorted(glob.glob(os.path.join(d, "*.png")))
        worst = 1.0
        for p in pngs:
            x0, x1, y0, y1 = coverage(p)
            cov = min(x1 - x0, y1 - y0)
            worst = min(worst, cov)
            flag = "  <- LOW (transform bug?)" if cov < 0.95 else ""
            print(f"  {os.path.basename(p)} coverage {x0:.2f}..{x1:.2f} x {y0:.2f}..{y1:.2f}{flag}")
        ok = ok and worst >= 0.95
    print("RESULT:", "OK" if ok else "CHECK FAILED")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()