#!/usr/bin/env python3
# Bold "brutalist" background pool for quote wallpapers, via the make-art engine (Gemini).
# Usage: python3 gen_backgrounds.py <out_dir>   (run with the Bash sandbox DISABLED — network)
import subprocess, os, sys
GEN=os.path.expanduser(os.environ.get("MAKE_ART_GEN","~/.claude/skills/make-art/scripts/gen_art.py"))
OUT=sys.argv[1] if len(sys.argv)>1 else "bgpool"
os.makedirs(OUT,exist_ok=True)

FIELD=("flat saturated color field, one hard black geometric shadow or wedge cutting across, heavy risograph and film grain, "
       "minimal graphic brutalist poster, extreme high contrast, subtle cream paper border, no text no lettering, vertical")
CELEST=("extreme high contrast, cinematic, heavy grain, immense negative space, ominous and monumental, no text no lettering, vertical")
BW=("high-contrast grainy black and white 35mm photograph, deep crushed blacks, one harsh raking light, stark, monumental, brutalist, vast negative space, no text no lettering, vertical")
SURR=("surreal, near-monochrome, harsh film grain, dramatic chiaroscuro, uncanny and dreamlike, brutalist, no text no lettering, vertical")

PROMPTS=[]
def add(scene, suf): PROMPTS.append(f"{scene}. {suf}")

# --- color fields (his favorite) ~16 ---
for scene in [
 "A field of deep vermilion orange bleeding into oxblood, a hard black diagonal wedge rising from the lower left",
 "A field of deep cobalt blue into black, a sharp black geometric shadow in the lower third",
 "A burnt orange field, a black rising diagonal shadow like a ramp",
 "An oxblood red field, a heavy black horizontal shadow band across the middle",
 "A mustard-ochre field into deep brown, one hard angular shadow",
 "A deep teal field into black, a single sharp triangle of pale light",
 "A crimson field, a black geometric corner biting in from the right",
 "A deep aubergine purple field, a hard black wedge",
 "A dark forest-green field, a black diagonal shadow",
 "A slate-grey field, a single burnt-orange accent block low",
 "A bone-and-sand field, an oxblood hard-edged shadow across the bottom",
 "An electric ultramarine field into black, a hard black shadow",
 "A rust-red field into charcoal, a sharp diagonal division",
 "A deep magenta field, a black angular wedge",
 "An amber field, a black stair-step shadow climbing across",
 "A vermilion field, a black inverted triangle descending from the top",
]:
    add(scene, FIELD)

# --- celestial / eclipse ~7 ---
for scene in [
 "An enormous black eclipsed sun ringed by a thin blazing white corona over a stark empty desert horizon",
 "A blood-red eclipse low over a black horizon, dark sky",
 "An enormous full moon low over black still water, a faint silver path",
 "Total darkness broken by a single perfect ring of cold light",
 "A white sun burning through thick black smoke, deep amber edges",
 "A pale planet rising over a black featureless plain, monochrome",
 "A dense star field with one enormous dark planet filling a corner",
]:
    add(scene, CELEST)

# --- stark B&W ~6 ---
for scene in [
 "A single tiny lone figure at the base of an immense blank brutalist concrete wall",
 "Endless brutalist concrete stairs receding into shadow",
 "A lone tiny figure crossing a vast white salt flat",
 "The stark silhouette of a lone dead tree against a blown-out white sky",
 "A single empty road vanishing to a point on the horizon",
 "A brutalist concrete tower against a black sky, one small lit window",
]:
    add(scene, BW)

# --- surreal ~6 ---
for scene in [
 "A lone figure dissolving into a towering stormcloud over black mountains, double exposure",
 "Ocean waves double-exposed over a human profile",
 "A single door standing alone in a desert, a long hard shadow",
 "Two moons hanging over a still black sea",
 "An empty wooden chair alone in an infinite white room",
 "A vast field of grey static and noise with one dark shape emerging",
]:
    add(scene, SURR)

def gen(i,p):
    out=f"{OUT}/{i:02d}.png"
    if os.path.exists(out) and os.path.getsize(out)>10000: print(f"[{i:02d}] skip"); return
    try:
        r=subprocess.run(["python3",GEN,"--prompt",p,"--out",out,"--aspect","9:16","--size","2K"],
                         capture_output=True,text=True,timeout=300)
        print(f"[{i:02d}] {'OK' if os.path.exists(out) else 'FAIL'} {r.stderr.strip()[:80]}")
    except Exception as e: print(f"[{i:02d}] ERR {e}")

for i,p in enumerate(PROMPTS): gen(i,p)
print("POOL2 DONE:", len([f for f in os.listdir(OUT) if f.endswith('.png')]))
