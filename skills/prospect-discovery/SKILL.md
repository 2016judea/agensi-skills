---
name: prospect-discovery
description: A discovery-call "problem map" — a notes form whose fields ARE the conversation, built to extract a prospect's problem in their own words instead of logging activity or pitching features. Use when designing or changing a sales-call notes form or CRM fields, coaching reps toward discovery instead of a feature dump, or turning a captured problem into the right thing to build or pitch.
---

# Prospect discovery (the problem map)

## Thesis

**If you can build them almost anything, the only hard part is understanding their problem.**
So the sales tool's job is not to log activity; it is to *extract the prospect's problem in
their own words*. The discovery form is a problem-extraction instrument disguised as a notes
box, and because filling it in *is* running the call, its field order quietly trains the rep
into a discovery posture instead of a feature dump.

## The arc (each field = one beat of the call + one slot of data)

| Field | The question the rep sees | Why it's there |
|---|---|---|
| `talked_to` | Who'd you talk to? | anchor, low-friction open |
| `goal` | What are they trying to pull off? | their goal, not our pitch |
| `problem` **(the gold)** | What's hard about it right now? | the actual discovery |
| `stakes` | What's it costing them to stay stuck? | urgency, deadline |
| `dream` | What would "handled" look like? | reverse-engineers the deliverable |
| `tried` | What have they already tried? | the gap you fill, and what not to repeat |
| `close` | What's the catch to a yes? | decision-maker, timeline, objection |
| `notes` | Anything else | loose ends |

Plus `contacted` (checkbox), `rep`, `updated` (last-edited time).

## Design principles (don't break these)

1. **Artifact-agnostic.** Never add a field that presupposes the product ("which plan do they
   want"). The moment it does, the rep stops listening and starts pitching. Ask what hurts;
   decide the deliverable afterwards.
2. **The empty box is the signal.** A blank `problem` means the rep didn't qualify; they just
   "called, not interested". Make the row preview in your list view show `problem` (falling
   back to free notes) so an un-discovered prospect looks empty at a glance.
3. **Prompts are questions to ask, not labels to fill.** "What's hard about it right now?", not
   "Pain:". The microcopy is the script.
4. **Their words, verbatim.** Quote the prospect in `problem` and `dream`. Paraphrase loses the
   language you will later sell back to them.

## Wiring it into a CRM or a sheet

Any store works (a CRM custom object, Notion, Airtable, a spreadsheet). Keep one column per
field above, upsert the full set on every save (so a cleared field really clears), and show
`problem` in the list view. Adding a field is: column in the store -> key in the save handler ->
read it back in the load handler -> one textarea in the form, with a question as its label.

## Closing the loop (problem -> deliverable)

A filled problem map is the brief. Map the captured `problem` and `dream` to the deliverable
that answers them and pitch that, never a generic catalogue:

- needs to prove numbers to a buyer or lender -> a diligence / valuation brief
- wants to understand a market before acting -> a market or sector read
- evaluating an acquisition or a property -> a deal underwrite
- wants reach or leads -> a lead list or a campaign

If none of your offers answers the `dream`, that is product discovery, not a lost deal. Record it.
