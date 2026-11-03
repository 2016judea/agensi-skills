#!/usr/bin/env python3
"""Assemble per-page PNG screenshots into a lossless print PDF with exact page boxes.

Usage: python3 assemble_pdf.py <PNG_DIR> <OUT_PDF> <dpi>
  <dpi> MUST equal the deviceScaleFactor*96 used in shoot.js (dsf 4 -> 384),
  or the page boxes will mis-size.

Uses img2pdf (no recompression). get_fixed_dpi_layout_fun makes each page box
exactly pixels/dpi inches -- e.g. 3312px @ 384dpi = 8.625in. Do NOT use
Pillow's Image.save(...pdf): it recompresses to JPEG (lossy).

Install once:  pip3 install --user img2pdf
"""
import sys, glob, os
import img2pdf

def main():
    if len(sys.argv) != 4:
        sys.exit("Usage: assemble_pdf.py <PNG_DIR> <OUT_PDF> <dpi>")
    png_dir, out_pdf, dpi = sys.argv[1], sys.argv[2], float(sys.argv[3])
    files = sorted(glob.glob(os.path.join(png_dir, "*.png")))
    if not files:
        sys.exit(f"No PNGs in {png_dir}")
    layout = img2pdf.get_fixed_dpi_layout_fun((dpi, dpi))
    with open(out_pdf, "wb") as f:
        f.write(img2pdf.convert(files, layout_fun=layout))
    sz = os.path.getsize(out_pdf) / 1e6
    print(f"wrote {out_pdf}  ({len(files)} pages, {sz:.1f} MB, {dpi:g} DPI)")

if __name__ == "__main__":
    main()