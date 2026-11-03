"""flip_screen.py — screen MLS listings for flip margin (70% rule) + a generic
levered-return calculator. Part of the `flip-deal-feed` skill.

Two jobs:

1. SCREEN — given listings + a per-city ARV benchmark, compute each property's
   Maximum Allowable Offer (MAO = 0.70 * ARV - rehab), flag the ones that clear,
   and rank by margin of safety. This is the triage that turns 200 listings into
   a handful worth driving to.

2. CALCULATE — a generic deal calculator (cash-in, monthly interest payment, net
   upside shown as a RANGE across the ARV band). Numbers stay generic on purpose:
   you pick a down-payment % and rate, no lender required. The ARV band is the
   honesty mechanism — a flip lives or dies on ARV minus all-in cost, so we never
   print a single fake-precise profit number.

Usage:
    from flip_screen import screen, deal, mao, rehab_estimate
    rows = screen(listings, arv_by_city)        # ranked prospects
    d = deal(purchase=160_000, rehab=50_000, arv=320_000)

CLI (runs the demo screen on 5 fictional listings):
    python3 flip_screen.py
"""
from __future__ import annotations

# Rehab $/sqft benchmarks (materials + market labor), from the standard flipper
# estimators (FlipperForce / REIkit / RealEstateSkills). Owner sweat labor
# can roughly halve the cosmetic tiers — but NOT licensed trades (roof, furnace,
# panel, main plumbing); keep those at full price or they fail inspection.
REHAB_PER_SQFT = {"cosmetic": 25, "moderate": 40, "gut": 75}

SELL_PCT = 0.07          # agent commission + seller closing
CARRY_PER_MONTH = 1_100  # taxes + insurance + utilities while holding
BUY_CLOSING = 4_000
ARV_BAND = 0.08          # +/- 8% credible band around the ARV point estimate
SEVENTY_RULE = 0.70


def rehab_estimate(sqft: int, level: str = "moderate") -> int:
    """Rough rehab budget from size + depth. Confirm onsite — this is a desk number."""
    return int(sqft * REHAB_PER_SQFT[level])


def mao(arv: float, rehab: float, rule: float = SEVENTY_RULE) -> float:
    """Maximum Allowable Offer. The 30% gap covers financing, holding, selling, profit."""
    return rule * arv - rehab


def deal(
    purchase: float,
    rehab: float,
    arv: float,
    down: float = 0.20,
    rate: float = 0.08,
    months: int = 6,
    reserve_pct: float = 0.10,
) -> dict:
    """Generic levered deal. Returns cash-in, monthly interest payment, and net
    upside as (low, mid, high) across the ARV band. No lender required."""
    project = purchase + rehab
    loan = (1 - down) * project
    monthly_payment = loan * rate / 12
    interest = monthly_payment * months
    carry = CARRY_PER_MONTH * months
    reserve = project * reserve_pct
    cash_in = down * project + BUY_CLOSING + reserve

    def net(arv_v: float) -> int:
        sell = arv_v * SELL_PCT
        return int(arv_v - purchase - rehab - interest - carry - BUY_CLOSING - sell)

    return {
        "cash_in": int(cash_in),
        "monthly_payment": int(monthly_payment),
        "loan": int(loan),
        "net_low": net(arv * (1 - ARV_BAND)),
        "net_mid": net(arv),
        "net_high": net(arv * (1 + ARV_BAND)),
    }


def cap_value(noi: float, cap: float) -> int:
    """Income-property value = NOI / cap rate. The commercial-lane valuation core."""
    return int(noi / cap)


def value_add(noi_now: float, noi_stabilized: float, market_cap: float, price: float) -> dict:
    """Commercial value-add: what repositioning NOI creates at the market cap.
    Every $1 of NOI growth = $1/cap of value. Returns the value created over the buy."""
    val_now = cap_value(noi_now, market_cap)
    val_stab = cap_value(noi_stabilized, market_cap)
    return {
        "going_in_cap": round(noi_now / price, 4),
        "value_in_place_at_market_cap": val_now,
        "value_stabilized": val_stab,
        "value_created_over_price": int(val_stab - price),
    }


def screen(listings: list[dict], arv_by_city: dict[str, float], level: str = "moderate") -> list[dict]:
    """Score + rank listings. Each listing needs: address, ask, sqft, city.
    Returns rows sorted by margin (MAO - ask), best first."""
    rows = []
    for lst in listings:
        arv = arv_by_city.get(lst["city"])
        if not arv:
            continue
        rehab = rehab_estimate(lst["sqft"], level)
        offer = mao(arv, rehab)
        margin = offer - lst["ask"]  # positive = clears the 70% rule at ask
        # GUARDRAIL 1 (learned the hard way): a cheap attached unit is not a
        # discounted house — townhomes/condos just price lower and use a lower ARV.
        attached = lst.get("type", "house").lower() in {"townhome", "townhouse", "condo"}
        # GUARDRAIL 2: if list price ~ AVM, there is NO discount — it's priced right.
        avm = lst.get("avm")
        priced_at_market = bool(avm and lst["ask"] >= 0.93 * avm)
        rows.append({
            **lst,
            "arv": int(arv),
            "rehab": int(rehab),
            "max_offer": int(offer),
            "margin_at_ask": int(margin),
            "clears_at_ask": margin >= 0 and not attached and not priced_at_market,
            "discount_to_offer_pct": round(100 * (lst["ask"] - offer) / lst["ask"], 1),
            "flag": "ATTACHED — not a SFR flip" if attached
                    else ("priced at AVM — no discount" if priced_at_market else ""),
        })
    return sorted(rows, key=lambda r: r["margin_at_ask"], reverse=True)


# Demo data: FICTIONAL listings shaped like a real first run. ARVs are desk
# estimates pending real sold comps (the grounded-search step in the skill).
_ARV_BY_CITY = {"Northside": 320_000, "Heights": 335_000, "Lakeview": 365_000, "Riverton": 310_000}
_DEMO = [
    # The trap this demo keeps: a cheap ATTACHED unit priced at its AVM looks like a
    # 50%-off distress sale against a detached-house ARV. Both guardrails catch it.
    {"address": "101 Example Pl", "city": "Northside", "ask": 160_000, "beds": 3, "baths": 2, "sqft": 1377, "type": "townhome", "avm": 160_431},
    {"address": "202 Sample St", "city": "Heights", "ask": 169_995, "beds": 2, "baths": 1, "sqft": 1115},
    {"address": "303 Test Ave", "city": "Lakeview", "ask": 249_999, "beds": 3, "baths": 1, "sqft": 1873},
    {"address": "404 Demo St", "city": "Riverton", "ask": 199_900, "beds": 3, "baths": 1, "sqft": 960},
    {"address": "505 Mock St", "city": "Heights", "ask": 214_900, "beds": 4, "baths": 2, "sqft": 1423},
]


if __name__ == "__main__":
    print(f"{'ADDRESS':<24}{'CITY':<18}{'ASK':>10}{'MAX OFFER':>11}{'MARGIN':>9}  VERDICT")
    print("-" * 86)
    for r in screen(_DEMO, _ARV_BY_CITY):
        verdict = "CLEARS AT ASK" if r["clears_at_ask"] else f"offer {r['discount_to_offer_pct']}% under"
        print(f"{r['address']:<24}{r['city']:<18}{r['ask']:>10,}{r['max_offer']:>11,}{r['margin_at_ask']:>9,}  {verdict}")
    print()
    d = deal(purchase=160_000, rehab=50_000, arv=320_000)
    print("Deal calc — 101 Example Pl @ $160K, $50K rehab, 20% down, 8%, 6mo:")
    print(f"  cash in ~${d['cash_in']:,} · ${d['monthly_payment']:,}/mo · "
          f"net upside ${d['net_low']:,} – ${d['net_high']:,} (mid ${d['net_mid']:,})")
