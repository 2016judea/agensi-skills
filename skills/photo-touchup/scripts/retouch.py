#!/usr/bin/env python3
"""
Conventional (non-AI) photo touch-up: denoise, upscale, sharpen, fix flat lighting.
Deps: opencv-python-headless, numpy (pip3 install --break-system-packages opencv-python-headless numpy)

Usage:
  python3 retouch.py in.jpg out.jpg
  python3 retouch.py in.jpg out.jpg --scale 2.0 --sharpen 0.2 --saturation 1.1
"""
import argparse
import cv2
import numpy as np


def retouch(src_path, out_path, scale=1.6, sharpen=0.15, saturation=1.06, quality=96):
    img = cv2.imread(src_path, cv2.IMREAD_COLOR)
    if img is None:
        raise SystemExit(f"could not read {src_path}")
    h, w = img.shape[:2]

    # 1. Mild denoise BEFORE upscaling — denoise after upscale/CLAHE amplifies jpeg blockiness
    #    into visible posterization/painted-looking patches. Bilateral (not fastNlMeans) —
    #    it's gentler and doesn't leave the same blotchy artifacts at 1.5-2x scale.
    denoised = cv2.bilateralFilter(img, d=5, sigmaColor=35, sigmaSpace=35)

    # 2. Upscale with cubic, not Lanczos — Lanczos over-crisps edges into halos at this step.
    upscaled = cv2.resize(denoised, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

    # 3. Light unsharp mask only. Do NOT add CLAHE/local-contrast here — combined with
    #    sharpening it produces visible tile-like posterization on skin and flat surfaces.
    #    If more "pop" is wanted, prefer step 5's global auto-levels over local contrast.
    blur = cv2.GaussianBlur(upscaled, (0, 0), sigmaX=1.5)
    sharpened = cv2.addWeighted(upscaled, 1 + sharpen, blur, -sharpen, 0)

    # 4. Gentle saturation lift — fixes flat/yellow indoor fluorescent lighting without
    #    looking processed. Keep this subtle (1.05-1.15); higher reads as an obvious filter.
    hsv = cv2.cvtColor(sharpened, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation, 0, 255)
    out = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    # 5. Global auto-levels on the L channel only (LAB space) — safe, mild contrast stretch.
    #    NOT cv2.createCLAHE (that's the tiled/local version that causes the posterization above).
    lab = cv2.cvtColor(out, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.normalize(l, None, alpha=8, beta=247, norm_type=cv2.NORM_MINMAX)
    out = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)

    cv2.imwrite(out_path, out, [cv2.IMWRITE_JPEG_QUALITY, quality])
    print(f"{w}x{h} -> {out.shape[1]}x{out.shape[0]}  ({out_path})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--scale", type=float, default=1.6)
    ap.add_argument("--sharpen", type=float, default=0.15)
    ap.add_argument("--saturation", type=float, default=1.06)
    ap.add_argument("--quality", type=int, default=96)
    args = ap.parse_args()
    retouch(args.src, args.out, args.scale, args.sharpen, args.saturation, args.quality)
