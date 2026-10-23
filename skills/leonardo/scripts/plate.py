#!/usr/bin/env python3
"""
leonardo/scripts/plate.py — one study sheet in Leonardo's hand, via the make-art engine.

  python3 plate.py --mode ink --subject "…" --out sheet.png [--aspect 3:4] [--size 2K]
  python3 plate.py --list-modes

Composes STEM(mode) + SUBJECT + TAIL, attaches the mode's real sheets as style anchors,
calls the make-art skill's gen_art.py (path from $MAKE_ART_GEN, else ~/.claude/skills/make-art/scripts/gen_art.py), and writes the prompt beside the image
(<out>.prompt.txt) so the plate stays reproducible. Stdlib only. Needs network access — see the make-art skill.
"""
import argparse, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent.parent
SHEETS = HERE / "sheets"
import os
GEN = pathlib.Path(os.environ.get("MAKE_ART_GEN") or (pathlib.Path.home() / ".claude/skills/make-art/scripts/gen_art.py")).expanduser()

def read(name):
    return (HERE / "prompts" / name).read_text().strip()

# mode -> (stem file, default writing, anchor sheets). Anchors are the sheets the STEM was measured off.
# Writing defaults follow the real sheets: the working pages are annotated, the chalk/metalpoint/linen
# studies mostly are not. "margin" is the only setting that produces text blocks, and it is the one the
# model leaks in — see SKILL.md "the writing leak".
MODES = {
    "ink":         ("stem-ink.txt",         "margin", ["shoulder-anatomy", "fetus-in-womb-rcin919102", "flying-machine"]),
    "codex":       ("stem-codex.txt",       "margin", ["codex-arundel-174v-175r", "codex-atlanticus-307v", "vitruvian-man"]),
    "chalk":       ("stem-chalk.txt",       "none",   ["self-portrait-turin", "grotesque-heads"]),
    "silverpoint": ("stem-silverpoint.txt", "none",   ["womans-hands-rcin912558", "horses-rcin912285"]),
    "linen":       ("stem-linen.txt",       "none",   ["drapery-seated-c1470"]),
    "deluge":      ("stem-deluge.txt",      "line",   ["deluge", "tuscan-landscape-1473"]),
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="ink", choices=sorted(MODES))
    ap.add_argument("--subject", help="one paragraph: what is on the sheet, as studies")
    ap.add_argument("--subject-file")
    ap.add_argument("--out", required=False)
    ap.add_argument("--aspect", default="3:4", help="3:4 = a folio; 4:3 = a landscape sheet; 1:1 square")
    ap.add_argument("--size", default="2K")
    ap.add_argument("--notes", choices=["auto","margin","line","none"], default="auto",
                    help="how much handwriting: auto = the mode's default")
    ap.add_argument("--no-anchor", action="store_true", help="prompt only, no reference sheets attached")
    ap.add_argument("--flip", action="store_true",
                    help="mirror the finished plate horizontally (sips). Turns the engine's right-handed / hatching "
                         "into Leonardo's left-handed \\ hatching; safe when the sheet has no writing or only pseudo-script")
    ap.add_argument("--list-modes", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="print the prompt and the command, spend nothing")
    a = ap.parse_args()

    if a.list_modes:
        for m, (stem, notes, anchors) in MODES.items():
            print(f"{m:12s} {stem:22s} notes={notes:7s} anchors: {', '.join(anchors)}")
        return
    if not a.out: sys.exit("--out is required")
    subject = a.subject or (pathlib.Path(a.subject_file).read_text().strip() if a.subject_file else None)
    if not subject: sys.exit("--subject or --subject-file is required")

    stem_file, default_notes, anchors = MODES[a.mode]
    notes = default_notes if a.notes == "auto" else a.notes
    prompt = "\n\n".join([read(stem_file), "SUBJECT — what is on this sheet:\n" + subject,
                           read(f"notes-{notes}.txt"), read("tail.txt")])

    out = pathlib.Path(a.out)
    cmd = [sys.executable, str(GEN), "--prompt", prompt, "--out", str(out), "--aspect", a.aspect, "--size", a.size]
    if not a.no_anchor:
        for s in anchors:
            cmd += ["--image", str(SHEETS / f"{s}.jpg")]
    if a.dry_run:
        print(prompt); print("\n$", " ".join(cmd[:6]), "…"); return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(out.suffix + ".prompt.txt").write_text(
        f"# mode={a.mode} notes={notes} aspect={a.aspect} size={a.size} anchors={'none' if a.no_anchor else ','.join(anchors)}\n\n{prompt}\n")
    rc = subprocess.call(cmd)
    if rc == 0 and a.flip:
        subprocess.check_call(["sips", "-f", "horizontal", str(out)], stdout=subprocess.DEVNULL)
        print(f"flipped {out} horizontally")
    sys.exit(rc)

if __name__ == "__main__":
    main()
