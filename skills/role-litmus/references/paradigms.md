# The paradigms this framework is assembled from

Researched (2026) before the framework was written, on the instruction to research other
paradigms for this sort of feedback QA before building. This file is the basis a reasoning
agent can check rather than inherit.

---

## Part 1 — why the obvious approach fails

The obvious approach is: write eight plausible customers, ask each what they think
of the page, collect the answers. There is a 2024-2025 literature on exactly that,
and it is unkind.

| Failure | Where it comes from | What it would do here |
|---|---|---|
| LLM-simulated populations **underestimate variance, miss minority opinions, and converge on the median web-text answer** | MIT / Cornell / Stanford, April 2025 | eight personas that all say one reasonable thing, and a synthesis that is the mean of a mean |
| **Sycophancy** — models are RLHF-trained to agree with the framing of the question | Anthropic's own work on sycophancy in language models; ACM *Interactions*, ["The Synthetic Persona Fallacy"](https://interactions.acm.org/blog/view/the-synthetic-persona-fallacy-how-ai-generated-research-undermines-ux-research) | a litmus test that always passes, because the framing supplied to it is *"isn't our platform useful"* |
| **Everything is equally important.** AI personas cite interactivity, personalisation, flexibility and rank none of them; real users weigh and prioritise | [Agile Brand Guide](https://agilebrandguide.com/synthesize-to-optimize-synthetic-personas-excel-at-audits-struggle-with-context/), 2025 | a want-list that decides nothing |
| **Training-data drift** — the model reflects web text from 2020-2023, not a 2026 customer | [Conversion Alchemy, *State of synthetic research in 2025*](https://christophersilvestri.com/research-reports/state-of-synthetic-research-in-2025/) | confident answers about a market that moved |
| **No capacity for genuine surprise.** In one study synthetic users reported completing every online course; real participants reported dropouts, no time, and motivation problems | [Perspective AI](https://getperspective.ai/blog/synthetic-focus-groups-why-fake-respondents-can-t-replace-real-customer-research); [uhura.de](https://www.uhura.de/en/blog/ai-personas-and-synthetic-users-fast-research-or-risky-illusion) | the failure state is a clean bill of health |

**The one positive finding, and it aims the whole design:** synthetic personas
*excel at audits* and *struggle with context*. So the framework points them at what
can be checked — does the file have the column, does the row count match the claim,
does the page state the limit — and keeps them away from *would you pay for this*.

It is the same failure as any guard that shares assumptions with the thing it checks: a
check built on the code's own model confirms the bug. A persona written by the people who built the product, and
allowed to read why the product is the way it is, will rationalise the product.

There is also a directly-on-point paper: **Synthetic Cognitive Walkthrough**
([arXiv 2512.03568](https://arxiv.org/pdf/2512.03568)), which runs an LLM through a
human cognitive-walkthrough protocol and measures agreement with human evaluators.
Its finding is the one worth carrying: **context-grounded prompting is the mechanism
that moves LLM findings toward human ones.** Grounding is not flavour. It is the
part that works.

---

## Part 2 — the four paradigms adopted, one per pass

### Cognitive walkthrough → pass 2
Wharton, Polson, Lewis & Rieman. A task-based usability *inspection* method: the
evaluator steps through every individual action a task requires and asks a fixed set
of four questions at each step.

1. Will the user try to achieve the right effect?
2. Will the user notice that the correct action is available?
3. Will the user associate the correct action with the effect they want?
4. After the action, will the user see that progress has been made?

**It measures learnability specifically**, not overall interface quality: whether a
visitor who doesn't know what they're looking for gets guided to it. A method that locates
*which step* loses the visitor is more use than another round of guidance mechanics.

Sources: [NN/g](https://www.nngroup.com/articles/cognitive-walkthroughs/),
[Usability BoK](https://www.usabilitybok.org/cognitive-walkthrough/),
[Waterloo course notes](https://cs.uwaterloo.ca/~jianzhao/cs449-649/files/walkthrough.pdf).

### The Mom Test → the prohibition, and pass 5's method
Rob Fitzpatrick. Three rules: **talk about their life, not your idea; ask about
specifics in the past, not opinions about the future; talk less.**

Adopted here as a *prohibition*, because the two questions everyone wants to ask a persona
are, asked directly, the forbidden question:

- ❌ "What tools do you want?" → ✅ what did you use the last time you needed this,
  and what did it cost you?
- ❌ "Would you use this?" → ✅ does this beat the thing you already pay for, and on
  which specific task?

A persona asked to predict its own future behaviour produces a polite lie — the same
polite lie a real interviewee produces, which is why the book exists.

Sources: [Looppanel summary](https://www.looppanel.com/blog/customer-interviews),
[Koji](https://www.koji.so/blog/mom-test-customer-interviews-2026).

### JTBD switch interview / four forces → pass 4
Bob Moesta & Chris Spiek. A switch happens only when **push + pull** beat
**anxiety + habit**:

- **Push** — what is wrong with the current situation
- **Pull** — the magnetism of the new thing and the progress it promises
- **Anxiety** — fear about the new, unproven choice
- **Habit** — the comfortable gravity of what they already do

This converts "would they use it" into a structured verdict against a *named*
incumbent, and it supplies the anti-sycophancy governor: **anxiety and habit are
non-zero by default**, so the verdict starts at *no change* and has to be moved.

Sources: [jobstobedone.org](https://jobstobedone.org/),
the 60-minute switch interview script (innovation-creativity.com).

### Kano → pass 5's sort
Noriaki Kano. Features classify as **must-be** (absent = angry, present =
unnoticed), **performance** (more is better, linear), **delight** (absent =
unnoticed, present = disproportionate love), **indifferent**, **reverse** (present =
worse). This is the direct fix for the documented "everything is equally important"
failure: a want-list that is Kano-sorted and capped cannot be flat.

---

## Part 3 — borrowed but not adopted as passes

- **Nielsen heuristic evaluation** — five independent evaluators find roughly 75% of
  issues; one evaluator finds far fewer. The transferable part is not the ten
  heuristics, it is *independence and deduplication*: several narrow evaluators beat
  one omniscient reviewer. Here, several personas, each blind to the others' findings.
- **Top Tasks** (Gerry McGovern) — a small number of tasks carry most of the value
  and a long tail carries almost none. Why the persona file caps top tasks at 3-5
  and why pass 2 walks only the **#1**.
- **RITE** (rapid iterative testing and evaluation) — fix after each participant
  rather than after the study. Why the recommended order runs two roles, reacts, then
  runs the rest.
- **5-second test / first-click test** — pass 1. A judgement formed from one
  screenshot with no scrolling is the honest simulation of a visitor arriving
  mid-scroll from a social feed.

Not adopted: SUS and HEART (both need real users and real N — a synthetic SUS score
is a number with no referent), and A/B testing (needs real traffic; this is for a product with
no traffic yet).
