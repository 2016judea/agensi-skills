"""cre_underwrite.py — levered underwriting for a commercial prospect.

Broker-grade returns on an income property: debt service, DSCR, cash-on-cash,
exit value at a cap, net sale proceeds, equity multiple, and levered IRR over a
hold. Models a value-add ramp (in-place NOI year 1 → stabilized NOI thereafter)
so a vacant-on-purchase deal (negative year-1 carry) underwrites honestly.

Part of the `flip-deal-feed` skill. Assumptions are explicit and generic — vary
down %, rate, and exit cap to see the sensitivity; no specific lender required.
"""
from __future__ import annotations


def debt_service(principal: float, rate: float, amort_years: int) -> float:
    i, n = rate / 12, amort_years * 12
    return principal * (i * (1 + i) ** n) / ((1 + i) ** n - 1) * 12


def balance_after(principal: float, rate: float, amort_years: int, years: int) -> float:
    i, n, k = rate / 12, amort_years * 12, years * 12
    return principal * ((1 + i) ** n - (1 + i) ** k) / ((1 + i) ** n - 1)


def irr(cashflows: list[float]) -> float:
    """Levered IRR via bisection. cashflows[0] is the (negative) equity outlay."""
    def npv(r: float) -> float:
        return sum(cf / (1 + r) ** t for t, cf in enumerate(cashflows))
    lo, hi = -0.99, 3.0
    for _ in range(300):
        mid = (lo + hi) / 2
        if npv(mid) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def underwrite(name, price, noi_in, noi_stab, capex, *, down=0.25, rate=0.07,
               amort=25, hold=5, exit_cap=0.065, sell=0.04, closing=0.02, stab_year=2):
    equity = price * down + price * closing + capex
    loan = price * (1 - down)
    ads = debt_service(loan, rate, amort)
    flows = [-equity]
    for y in range(1, hold + 1):
        noi = noi_in if y < stab_year else noi_stab
        cf = noi - ads
        if y == hold:
            exit_val = noi_stab / exit_cap
            cf += exit_val * (1 - sell) - balance_after(loan, rate, amort, hold)
        flows.append(cf)
    distributions = sum(flows[1:])
    return {
        "name": name, "price": price, "equity": equity, "loan": loan, "ads": ads,
        "cap_in": noi_in / price, "dscr_in": noi_in / ads, "dscr_stab": noi_stab / ads,
        "coc_stab": (noi_stab - ads) / equity, "exit_val": noi_stab / exit_cap,
        "profit": distributions - equity, "equity_mult": distributions / equity,
        "irr": irr(flows),
    }


# Demo deals: FICTIONAL, shaped like real small-multifamily / light-industrial listings.
_DEALS = [
    # Listing NOI often omits insurance; correct it before underwriting.
    dict(name="8-unit walk-up", price=795_000, noi_in=46_851, noi_stab=58_000, capex=60_000, exit_cap=0.065),
    # Rents already at market; NOI self-managed with reserves.
    dict(name="7-unit, at-market rents", price=795_000, noi_in=52_000, noi_stab=57_000, capex=35_000, exit_cap=0.070),
    # VACANT year 1 (negative carry), then lease up single-tenant NNN.
    dict(name="Small warehouse (vacant)", price=700_000, noi_in=-12_000, noi_stab=52_000, capex=40_000, exit_cap=0.065),
]

if __name__ == "__main__":
    print("Base case: 25% down · 7.0% · 25-yr amort · 5-yr hold · 4% sale cost\n")
    hdr = f"{'DEAL':<24}{'EQUITY':>10}{'CAP-IN':>8}{'DSCR-in':>9}{'CoC*':>7}{'EXIT':>10}{'PROFIT':>10}{'MULT':>6}{'IRR':>7}"
    print(hdr); print("-" * len(hdr))
    for d in _DEALS:
        r = underwrite(**d)
        print(f"{r['name']:<24}{r['equity']:>10,.0f}{r['cap_in']*100:>7.1f}%{r['dscr_in']:>9.2f}"
              f"{r['coc_stab']*100:>6.1f}%{r['exit_val']:>10,.0f}{r['profit']:>10,.0f}"
              f"{r['equity_mult']:>6.2f}{r['irr']*100:>6.1f}%")
    print("\n*CoC = cash-on-cash at stabilization. Exit = stabilized NOI / exit cap.")
    print("\nExit-cap sensitivity on levered IRR:")
    for d in _DEALS:
        line = f"  {d['name']:<24}"
        for ec in (0.060, 0.065, 0.070, 0.075):
            r = underwrite(**{**d, "exit_cap": ec})
            line += f"  {ec*100:.1f}%:{r['irr']*100:>5.1f}%"
        print(line)
