---
name: melville-annotated-shakespeare
description: Build a personal print edition of a Shakespeare play with Herman Melville's real marginalia (his pencil marks and written comments from his own annotated copy) reproduced in the margins at the right lines. Use when you want this for any play Melville marked — e.g. "do the Melville thing for Hamlet/Othello/Romeo and Juliet."
compatibility: >-
  Python 3 and headless Chrome. Fetches public TEI-XML and play text at use time; nothing third-party ships with the skill.
metadata:
  network-hosts: "melvillesmarginalia.org shakespeare.folger.edu"
  network-purpose: "download a marginalia volume and a play text for a personal edition"
---

# melville-annotated-shakespeare

Reproduces Herman Melville's actual marginalia — from his own annotated 1837 copy of Shakespeare's *Dramatic Works*, now digitized by [Melville's Marginalia Online](https://melvillesmarginalia.org) (Boise State, dir. Steven Olsen-Smith) — onto a clean modern Folger text of the same play, laid out for print. Built first for *King Lear*.

**The two source facts that make this possible:** Melville's copy is real and preserved at Harvard's Houghton Library (Sealts #460, 7 volumes), and Melville's Marginalia Online has transcribed it as TEI-XML that's freely downloadable in one request per volume. Folger Shakespeare Library separately gives away clean, modern-spelling play texts as plain `.txt` under CC BY-NC 4.0. Neither alone is a book; stitched together, they are.

## Before you start: check the play actually has marks

**Not every play is annotated.** Melville marked Lear and Hamlet heavily; he left *zero* marks in Macbeth, Comedy of Errors, and King John (confirmed by mark counts — see below). Don't build the whole pipeline before checking.

```bash
python3 scripts/list_plays.py --play macbeth
# DocId 27  pp. 171-262     0 marks  Macbeth  <-- NO MARKS, skip
```

Run with no `--play` filter to see the whole 7-volume table of contents with mark counts. This hits the live site (Viewer.aspx page index + XML mark counts for every volume), takes ~30s.

**Known volume map** (Dramatic Works, DocId 25–31 = Vol. 1–7; DocId 32 is a separate 1865 Sonnets volume):
- Vol. 7 (DocId 31): King Lear (pp. 3–134, **52 marks**), Romeo and Juliet (135–246), Hamlet (247–394), Othello (395–518)
- Vol. 3 (DocId 27): Winter's Tale (3–108), Comedy of Errors (109–170, 0 marks), **Macbeth (171–262, 0 marks)**, King John (263–354, 0 marks), King Richard II (355–452), King Henry IV Pt.1 (453–556)
- Vols 1, 2, 4, 5, 6: not yet surveyed — run `list_plays.py` for these.

## Pipeline

1. **Confirm the target play has marks** (`list_plays.py`, above).

2. **Fetch sources:**
   ```bash
   python3 scripts/fetch_sources.py --doc-id <N> --folger-slug <slug> --outdir work/
   ```
   `--folger-slug` is the slug in Folger's own URL, e.g. `king-lear`, `hamlet`, `othello`, `romeo-and-juliet` — check `https://shakespeare.folger.edu/shakespeares-works/<slug>/` if unsure.

3. **Render + match:**
   ```bash
   python3 scripts/render_annotated_play.py \
     --xml work/vol<N>_raw.xml --page-start <S> --page-end <E> \
     --folger-text work/<slug>_folger.txt \
     --title "The Tragedy of <Play>" --volume <7> \
     --style antiquarian \
     --out work/play_annotated.html
   ```
   This auto-matches Melville's marked passages to lines in the Folger text (sequential fuzzy matching — reliable because marks are already page-ordered) and prints a report. ~80–90% match cleanly; the rest print as "WEAK, check by hand."

4. **Fix weak matches by hand.** For each weak line, `grep` the Folger text for a distinctive fragment from its `note=` field to find the real line, then add `"page,y": line_index` to a JSON overrides file (see `lear_overrides.json` for a worked example — that file has King Lear's 8 corrections). Pass it back in with `--overrides corrections.json` and rerun step 3. Two other things you may need to special-case:
   - **Bare-content marks** (e.g. a lone `"Cor."` speech prefix, or a single word split oddly by the OCR) usually aren't wrong, just short — don't force a fix if the anchor already looks right.
   - **Trailing editorial notes.** This 1837 edition appends critical essays (Johnson-style) after some plays, inside the play's own page range. If a weak match's `note=` text obviously isn't dialogue, pass its page number via `--appendix-pages <N>` — it'll be collected as a closing "Editor's Notes" section instead of forced onto a real line.

5. **Pick a style** (`--style antiquarian|brutalist|modern_serif`, or add a new block to `STYLES` in `render_annotated_play.py`). Render all three and compare before committing — see the style note below.

6. **Print to PDF:**
   ```bash
   ./scripts/print_pdf.sh work/play_annotated.html work/play_annotated.pdf
   ```
   No installs needed — uses headless Chrome. `--no-pdf-header-footer` is required or Chrome stamps a date/URL/page-number header on every page.

7. Sanity-check a few pages (`pdftoppm -png -r 130 -f N -l N file.pdf preview` + Read the PNG) before calling it done, especially the pages with the real written annotations (search `pdftotext file.pdf -` for a distinctive quote).

## Design decisions worth keeping

- **Only Melville's own written words get a quoted sidenote.** Marks over the printed text (underline, score, checkmark, cross-check, X, bracket) render as a *visual* mark only — never as invented descriptive text like "Melville underlined this passage." The marks should speak for themselves.
- **"Score" marks render as a vertical bar in the margin, not underlining.** That's what "scored in the margin" physically meant in period annotation practice — a line drawn beside the passage, spanning its full length, not through the text.
- **Style choice isn't automatic from house taste.** For an artifact that carries someone else's historical material, the quiet **Antiquarian** direction beat a bold brutalist one in the first build. Offer Antiquarian first; still render 2–3 options since the choice is real.
- **Binding:** recommend FedEx Office spiral/comb binding over stapled or perfect-bound — it's the only option that lets a script-format book lie flat open, which matters since the reader is flipping to the margin constantly.

## Gotchas

- **`text-decoration` bleeds into a sibling `::before` pseudo-element's glyph.** Putting the checkmark glyph in `.checkmark::before` on the *same* element that also carries `text-decoration:underline` visually mangles the glyph (a ✓ rendered as garbled "13" under a thick colored underline). Fix: underline only an inner `<span class="underlined">` wrapping the real text; keep the checkmark as a separate sibling `<span class="checkmark">`, never nested under the underline.
- **CSS unicode-escapes inside a non-raw Python triple-quoted string are dangerous.** `"\2713"` risks Python reading `\271` as an octal escape (digits 2/7/1 are all valid octal) before "3" is left dangling. Just embed the literal UTF-8 character (`"✓"`) directly instead of `"\2713"`.
- **Folger's download URL redirects** (short-link → S3); `urllib.request` follows redirects by default so `fetch_sources.py` doesn't need special handling, but if you swap in `requests` remember `allow_redirects=True`.
- **Chrome's default print header/footer** (date/URL/page-number) only goes away with `--no-pdf-header-footer` — easy flag to drop by accident when re-running commands by hand.
- **Textual variants are real, not bugs.** Melville's 1837 edition sometimes reads differently from the modern Folger text (e.g. his Lear has Cordelia's "nothing *can* come of nothing," Folger has "nothing *will* come of nothing" — a genuine Quarto/Folio-lineage difference). The fuzzy matcher tolerates small wording gaps; don't chase a "perfect" score on every line.

## Files in this skill

- `list_plays.py` — discover DocId + page range + mark count for any play across all 7 volumes.
- `fetch_sources.py` — download a volume's marginalia XML + a play's Folger text.
- `render_annotated_play.py` — match + render to HTML (3 built-in style presets: `antiquarian`, `brutalist`, `modern_serif`).
- `print_pdf.sh` — headless-Chrome HTML→PDF wrapper.
- `lear_overrides.json` — worked example of the manual-correction file format, from the King Lear build.

## Licences

Nothing third-party ships with this skill; the scripts fetch at use time. Melville's Marginalia Online
material and the Folger text (CC BY-NC 4.0) are for **personal, non-commercial** editions: keep the
Folger attribution on the title page and don't sell the result.
