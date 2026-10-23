---
name: sms-native-product
description: >
  Build a product whose interface is text messages rather than an app or a website —
  "no app, no website", "they just text a number", "chat with our agent natively in
  Text Messages", "can we do this over text", "an SMS bot", "a Telegram bot", "make it
  a group chat", "minimum viable friction". Fires equally when it has already gone
  wrong — "my campaign got rejected", "our number is blocked", "the texts aren't
  arriving", "why do I need to register". Covers the gate that decides whether such a
  product can send at all (US A2P 10DLC registration, SHAFT content rules, permanent
  rejection codes), group MMS from code, what each channel can't do, an architecture
  that survives losing the channel, and guarding model-rewritten user content.
---

# Products whose interface is text messages

The appeal is real: people don't like installing apps or visiting websites, but everyone
can text. The catch is that **you do not own the channel.** US carriers do, and they have a
content policy and an approval process that can refuse you permanently. That gate decides
what the product is allowed to be, so it goes first.

---

## Step 0 — the gate. Do this before design, not after.

Since Feb 2025 US carriers block unregistered A2P traffic outright, so a brand and campaign
must be approved before a single message sends. **Re-read the live error docs every time;
carrier policy moves.**

| Code | Trigger | Resubmit? |
|---|---|---|
| [30953](https://www.twilio.com/docs/api/errors/30953) | explicit/suggestive language, **or a linked site hosting "pornographic, escort, dating, or adult entertainment content"** | **No** |
| [30885](https://www.twilio.com/docs/api/errors/30885) | "high risk" — deceptive marketing, or a registration that misrepresents the traffic | **No** |
| [30898](https://www.twilio.com/docs/api/errors/30898) | too many brands on one EIN, or a duplicative-looking registration | Yes, with cause |

**Rule: name the product's content category out loud in the first reply, and say whether it
is on that list.** If the category (e.g. dating) is literally a keyword in a rejection rule,
finding that in minute five changes the architecture, the landing copy and the fallback plan.
SHAFT is the shorthand: Sex, Hate, Alcohol, Firearms, Tobacco — plus Cannabis, and dating
rides alongside.

**Rule: register a side project as a Sole Proprietor brand, not under an existing company's
EIN.** Risk patterns follow the tax ID (30898), so a refusal on a side project must not touch
your main business's ability to send. Sole Proprietor is scoped to individuals with no Tax ID;
throughput is low, and low is plenty for a beta.

**Rule: never build a decoy landing page to get a campaign approved.** A page that hides what
the traffic actually is *is* the 30885 pattern, and it converts a one-number risk into an
every-number-you-ever-register risk. State the odds plainly and let the owner decide.

**Describe the service by what it mechanically does**, and only if that is true (e.g.
journaling and small-group accountability, when that is what the messages are). If no true
description clears the gate, the answer is a different channel, not a better euphemism.

Vetting rewards facts you can point at: inbound-only opt-in, conversational volume, no links
in recurring messages, STOP handled ahead of everything, explicit content refused at the door.

## Step 0.5 — read the brief for NUMBERS and OBJECTS, not for intent

Keep the founder's brief verbatim as `README.md` and say in `CLAUDE.md` that it outranks every
engineering doc.

**Rule: before writing a state machine, list every duration in the brief and every noun it
acts on. If two durations exist, they are two features.** A brief with a one-week delay on
*friends' replies reaching the author* and a two-week lock on *the author's own update* is
easy to collapse into one seven-day hold on *the entry* — the one object neither delay was
about — and every downstream error follows from that merge.

**Rule: name the object of every delay — "held FROM whom".** Held from the friends and held
from the author are opposite products.

**Rule: when the brief's literal design can't be enforced on the channel, say so and give the
alternatives — don't silently pick the enforceable one.** (The creator of a group chat is a
member of it, so no code can withhold the group's replies from them.) That is a premise
decision, and premise decisions are the owner's.

**A coherent misreading does not feel like one.** Keep a superseded design paragraph struck
through in place rather than deleting it; it shows a later session *how* the brief was misread.

## Step 1 — what the channel can and cannot do

- **Group texting from code works.** Twilio Conversations does group MMS on **+1 long codes
  only** — not toll-free, not short codes — capped at **10 participants including your own
  number**. Don't assert otherwise from memory.
- **Group-MMS SMS participants carry an Address and no ProxyAddress**, so one number serves
  every room — but the participant/proxy uniqueness rule
  ([50425](https://www.twilio.com/docs/api/errors/50425)) has **no documented behaviour** for
  proxy-less participants. **Never design many concurrent rooms that share one number and one
  participant set.** One durable room per person has a stable participant set.
- **A webpage cannot read an iPhone address book.** The Contact Picker API is Chrome-on-Android
  only. "Sync your contacts" is dead on arrival; replace it with a line the user forwards — the
  recipient's inbound text is the consent record carriers want anyway.
- **A Telegram bot cannot create a group or add anyone to one**, and with privacy mode on it
  only hears commands addressed to it. Both help: the creator adds the bot to the chat they
  already have, and general chatter can't be mistaken for input. Creating a bot needs a human
  in @BotFather (no API); ask for the token.
- **WhatsApp Cloud API has no group messaging.**
- **iMessage APIs** (Sendblue, LoopMessage) do blue bubbles and real group chats, but cost
  around $100/line/month plus setup fees.

## Step 2 — architecture that survives losing the channel

Because the channel can be refused, **the transport must be one file**:

```
machine.js   pure: (context, event) -> {replies, effects}    no I/O, no clock
engine.js    context assembly -> machine -> effects          the whole path
effects.js   createEffects({db, channel})                    performs decisions
twilio.js  / telegram.js                                     interchangeable
api/*.js     thin shims over engine.js                       ~10 lines each
sim/         in-memory db + console channel
```

- **The decision core takes `now` as an argument and touches no network.** Every bug in this
  class of product is a sequencing bug (a reminder that fires twice, a message to an empty
  room, a held item that never lands), and none are testable against a live network and a
  seven-day timer.
- **Adapters are arguments, never imports, in the effects layer** — the same refactor the
  simulator and the fallback channel need.
- **No logic inside an HTTP handler.** Channel-specific onboarding written inside
  `api/telegram.js` is untestable; extract it.

## Step 3 — drive it, don't just test it

```
node sim/drive.js          scripted: the full loop, a week jumped, the guards
node sim/drive.js --repl   type as any number; /as <n>  /jump <days>  /state
```

- **The simulator must run the production path**, not a parallel copy.
- Expect a first drive to surface several real defects unit tests can't reach: a room that
  greets itself before anyone is in it, a bare weekday for a date a week out, a reminder that
  doesn't say which item it means, a room whose members all left.
- **When a test goes red, check the test first** (a date regex that doesn't allow the comma in
  `Sun, Aug 30`; a `doesNotMatch` that fires on a different, legitimate message).
- **Never decide or print from a store-stamped timestamp.** The store writes `created_at` from
  the real clock, not the engine's injected `now`, so under a jumped clock it lies (and prints
  dates in the past). Decide only from columns the machine wrote, and hang related dates off
  one stored anchor.

## Step 4 — copy for a lock screen

One file holds every outbound string.
- No emoji, no exclamation marks, no marketing.
- **Never a bare weekday for a date more than a day or two out.** `Sun Aug 30`.
- Forgive punctuation and case on every keyword — `Wait.` and `Yes!` must land.
- Prose containing a keyword is still prose: "we should wait and see" is not WAIT. Match the
  whole canonicalised message, never a substring.
- **STOP / HELP / START are parsed before all application state and before any model call**,
  so opt-out can't be broken by a bug elsewhere or an API outage.
- If a model guards content, **fail closed**: if the check can't run, send nothing and say so.

## Step 5 — if a model rewrites user content, run it before trusting it

A guard that strips third-party names from user entries can read perfectly and still:
1. **Invent a fact** — asked to replace "Jane Doe" with "a natural handle", it wrote "the girl
   from the app" when nothing mentioned an app; recipients read a fabrication as fact.
2. **Over-correct and delete real detail** — "Jane from the run club" became "her".

**Rule: the instruction must say what the model may NOT invent and what it may NOT delete.**
The working form: ground the substitution in the source, replace the *token* not the phrase
around it, and prefer a neutral fallback over reusing a detail the sentence already states.

**Rule: pin each live-model defect as an opt-in test, skipped without an API key**, so prompt
edits can't silently regress them without running up costs on every test run. Budget 2-5s per
guard call.

## Costs (order of magnitude; confirm live)

A +1 long code is a dollar or two a month; SMS under a cent a segment each way; MMS a few
cents. Sole Proprietor registration is a few dollars one-time plus a small monthly campaign
fee. Telegram is free.

## Ask vs. decide

- **Ask:** whether to submit an honest registration knowing it may be refused permanently, or
  start on Telegram (money and an irreversible outcome); anything that changes what the
  product *is*.
- **Decide:** architecture, copy voice, the state machine, test coverage, which adapter first,
  date formats, guard behaviour.

**Before reporting anything as blocked, enumerate every candidate credential** (one exhausted
API key on disk doesn't mean there isn't another that works).

**See also:** `build-remote-mcp-server` (another "native surface" pattern).
