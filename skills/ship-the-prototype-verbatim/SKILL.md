---
name: ship-the-prototype-verbatim
description: An approved mockup or prototype IS the spec: same copy, order, type sizes, widths, insets, colours and interactions. Port its markup and CSS rather than rebuilding it in a house template, then diff prototype and production side by side at 390px and 1440px. Use when moving an approved artifact/mockup/design into production.
---

# Ship the Approved Prototype Verbatim

**Rule.** If they approved it, that render is what they signed off on. Ship that, not an approximation.

**Why.** An approved page mockup was re-authored inside the site generator's existing CSS: a prose width cap
shrank it to a 600px column, headings went lowercase, the contact block was replaced by a line nobody approved,
and a caption was added. *"if i approve a prototype thats what i signed off on. not some half baked
implementation."*

**How to apply.**
- Port markup and CSS directly, scoped to the page. Don't re-word, add or drop lines.
- Screenshot prototype and production at 390 and 1440, side by side. List every difference.
- Ship when the list is empty or each item is a stated, deliberate exception (real asset paths). Say any
  unavoidable difference before they find it.

**Related:** `judge-at-full-size`, `vary-the-interaction`
