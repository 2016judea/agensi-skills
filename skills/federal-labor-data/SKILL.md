---
name: federal-labor-data
description: Use when a task needs real, current U.S. government data by industry or sector — job openings, wages, new-business formation — for a report, essay, benchmark, or sector-enrichment pass. Covers exact BLS JOLTS and OEWS series-ID formats and the Census Business Formation Statistics file, verified against live API responses (2026).
compatibility: >-
  Network access to public U.S. government APIs; the Census key is the user's own.
metadata:
  network-hosts: "api.bls.gov api.census.gov www.census.gov"
  network-purpose: "BLS JOLTS/OEWS series and Census Business Formation Statistics"
---

# Federal Labor & Business Data

Three free, no-key (or already-keyed) government sources cover almost every
"how's sector X doing" question, but their series-ID formats are
undocumented enough that guessing wastes real time. This skill has the
formats pre-verified against live API responses — use them directly instead
of re-deriving.

**Hard rule: never guess a series ID and ship the result.** Every code below
was confirmed by an actual API response, not inferred from a pattern. If you
need a sector not listed here, test the candidate ID live (see
"Verification pattern") before using the number in copy.

## Job openings — BLS JOLTS

`POST https://api.bls.gov/publicAPI/v2/timeseries/data/` with JSON body
`{"seriesid": [...], "startyear": "2025", "endyear": "2026"}` — no key needed
under 25 series/day.

Series ID: `JTS` + 6-digit industry code + `000000000` + `JOR` (rate) or `JOL` (level).

Verified industry codes (this is a distinct JOLTS-specific code list, NOT
just the NAICS 2-digit number — some coincide, most don't):

| Code | Industry |
|---|---|
| `000000` | Total nonfarm |
| `230000` | Construction |
| `440000` | Retail Trade |
| `530000` | Real Estate and Rental and Leasing |
| `540099` | Professional and Business Services |
| `600000` | Education and Health Services (supersector) |
| `610000` | Educational Services |
| `620000` | Health Care and Social Assistance |
| `700000` | Leisure and Hospitality (supersector) |
| `710000` | Arts, Entertainment, and Recreation |
| `720000` | Accommodation and Food Services |
| `810000` | Other Services (catches auto repair AND salons/personal care — no split beneath this level) |

## Pay — BLS OEWS

Same endpoint. Series ID is 25 characters: `OEUN` + `0000000` (7-char area
code, all-zero = national) + 6-digit NAICS industry code + `000000`
(occupation code, all-zero = all occupations) + 2-digit data type.

Data type `04` = annual mean wage. `15` = annual 90th-percentile wage.
**OEWS caps at the 90th percentile — there is no 99th-percentile series for
any industry. Don't fabricate one; say plainly that's the federal ceiling.**

Example: `OEUN000000072200000000004` = national annual mean wage, NAICS
722000 (Food Services and Drinking Places).

## New-business formation — Census BFS

Two different products, don't blend their vintages in one chart:

- **High-propensity business applications (HBA)**, monthly — Census API
  `https://api.census.gov/data/timeseries/eits/bfs`. **The field names are
  not what they look like at first glance — verified working query below,
  don't reconstruct from intuition:**
  - `get=cell_value,time_slot_id` (NOT `get=BA_HBA,...` — `BA_HBA` is a
    *filter value*, not a column to request; asking for it in `get` 400s
    with `unknown variable 'BA_HBA'`)
  - `data_type_code=BA_HBA` (the actual data-type filter)
  - `category_code=<code>` — **not** `NAICS2017=<2-digit code>`. Valid
    codes are prefixed strings, not raw numbers: `NAICS72` (Accommodation
    & Food), `NAICSRET` (Retail Trade — note: not `NAICS44` or `NAICS45`),
    `NAICS54` (Professional/Scientific/Technical), `NAICS23`
    (Construction), `NAICS81` (Other Services), `NAICS11`, `NAICS21`,
    `NAICS22`, `NAICS42`, `NAICS51`, `NAICS52`, `NAICS53`, `NAICS55`,
    `NAICS56`, `NAICS61`, `NAICS62`, `NAICS71`, `NAICSMNF` (Manufacturing),
    `NAICSTW` (Trade & Warehousing), `NONAICS`, or `TOTAL` (all
    industries). Full list is self-documenting: drop `category_code`
    entirely and query one month with no filter to see every valid code
    and its current value.
  - `seasonally_adj=no`, `time=from YYYY-MM to YYYY-MM` (range) or a single
    `YYYY-MM`.
  - Working example: `https://api.census.gov/data/timeseries/eits/bfs?get=cell_value,time_slot_id&time=from+2019-01+to+2026-06&for=us:*&category_code=NAICS72&data_type_code=BA_HBA&seasonally_adj=no&key=<CENSUS_API_KEY>`
  - Compare the same calendar month year-over-year, or sum 12 months for an
    annual total (NSA data isn't smooth month to month).
- **Total business applications (BA)**, 3-digit NAICS, weekly — flat file
  `https://www.census.gov/econ/bfs/csv/naics3.csv`. Sum the `YYYYwNN`
  columns for a full calendar year to get an annual total; most recent
  complete year lags the current date by several months, so "this year" in
  copy is usually last year, not the current one — say so explicitly.

## Verification pattern

```python
import urllib.request, json
body = json.dumps({"seriesid": ["JTS540099000000000JOR"], "startyear": "2025", "endyear": "2026"}).encode()
req = urllib.request.Request("https://api.bls.gov/publicAPI/v2/timeseries/data/", data=body,
                              headers={"Content-Type": "application/json"})
resp = json.loads(urllib.request.urlopen(req).read())
# resp["Results"]["series"][0]["data"] is empty + a "does not exist" message in
# resp["message"] if the code is wrong — don't retry blindly, look up the
# correct code (gemini-web-search / grounded search) instead of guessing again.
```

## Common mistakes

| Mistake | Fix |
|---|---|
| Assuming a JOLTS industry code matches the NAICS 2-digit number | Some do (`230000`≈23 Construction), most don't (`540099` for 54-56 Professional/Business Services). Test live. |
| Blending HBA (high-propensity) and BA (total applications) figures in one chart | Different metrics, different vintages — pick one product per chart and footnote which. |
| Inventing a 99th-percentile pay figure | OEWS doesn't publish one. Say so; don't extrapolate. |
| Presenting "this year" for BFS annual data | The weekly file's most recent complete year is usually the year before last-calendar-year — state the actual two periods being compared. |
| Requesting `get=BA_HBA,...` or filtering with `NAICS2017=72` on the BFS timeseries endpoint | 400s. Use `get=cell_value,time_slot_id` + `data_type_code=BA_HBA` + `category_code=NAICS72` (prefixed string, and `NAICSRET` for retail, not `NAICS44`). See worked example above. |

