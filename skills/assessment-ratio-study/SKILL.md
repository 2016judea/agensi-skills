---
name: assessment-ratio-study
description: Judge whether a county assessor values property fairly from recorded sales — "are cheap homes over-assessed", "is the assessor regressive", "ratio study", "sales ratio", "COD / PRD / PRB", "are neighbourhoods mis-taxed", "does the income model / cap rate hold up", "compare county vs city assessor". Residential or commercial. Covers the filters that decide the verdict, the IAAO statistics that are safe to quote, the tests that separate a real tilt from sale-price noise, and comparisons that look rigorous and are not.
---

# Assessment ratio study

A ratio is **assessed value / arm's-length sale price**. The assessor is fair when that ratio is
flat: flat across price levels (vertical equity), flat across neighbourhoods, and tightly bunched
(low dispersion). Standards: the IAAO *Standard on Ratio Studies* (COD, PRD, PRB). Theory worth
reading first: Berry (2021) on measurement error in regressivity, and Avenancio-León & Howard (QJE
2022) on the assessment gap.

## Rules, each with its why

1. **Filter to arm's-length sales, or report nothing.** Use the deed/sale-type code (e.g. warranty
   deeds only), drop multi-parcel deeds, and set a price floor (e.g. >= $50k). *Why:* family
   transfers and foreclosures cluster at the low end; stripping that filter moved one county's PRD
   from 1.024 to 1.155, which fakes a regressivity result. A county that publishes no sale code
   **cannot be measured** — say so and stop.
2. **Match the sale cohort to the assessment vintage.** Use sales from the assessment year (or the
   most recent). Many parcel exports carry only the last sale, and a decades-old sale against this
   year's value measures appreciation.
3. **State the trim every time.** 0.2-5.0 to find mis-assessed parcels; 0.5-2.0 to judge an office.
   The trim alone can flip a county between failing and passing the COD standard.
4. **Quote COD, PRD and PRB. PRB wins when PRD disagrees.** PRD is outlier-sensitive; on commercial
   property it often reads regressive where PRB doesn't. Then the defensible claim is *dispersion*,
   not a tilt.
5. **Never regress ln(ratio) on ln(sale price) and call the slope regressivity.** Sale noise sits on
   both sides, so the slope is negative even under a perfect assessor — worst within a tract, where
   price barely varies (one within-tract slope went from -0.168 on price to -0.071 on PRB's proxy
   1/2(AV/median) + 1/2·price, and +0.056 on AV). Report the proxy, or bound between the two.
6. **For neighbourhood bias, use regressors that carry no sale noise**: the leave-one-out tract mean
   price, or tract ACS attributes; and compare how ln(price) and ln(AV) load on those attributes.
   Measurement error can't produce those results (Berry §V).
7. **Never compare R^2 of price on AV across markets or property types.** R^2 rises with the spread of
   values, not with accuracy: on the same rows with the same COD, R^2 fell from .88 to .12 as the
   price band narrowed.
8. **A cap-rate gap alone doesn't size a value gap.** V = NOI / cap, so you need the assessor's NOI
   too. An office that "uses no mass-appraisal model" may be quoting a reference band it doesn't
   apply mechanically. Vendor cap-rate tables (PwC, CoStar, RERC) are licensed: use them for private
   reasoning, never redistribute.
9. **Bootstrap anything with n < 100 before calling a difference.** A class with n=35 had a COD 95%
   interval of 13-32, which makes comparing its COD to anything meaningless.

## Recipe

- **Parcels + sales:** the county's parcel layer (often ArcGIS FeatureServer — page past the 2,000-row
  cap) with assessed value, last sale price/date/code, property type, lat/lon. Cast numeric columns
  explicitly; they often arrive as text.
- **Tracts:** Census TIGER tract shapefile, joined with DuckDB `spatial` `ST_Contains`. Pin your pip
  `duckdb` to the version your spatial extension supports.
- **Tract attributes:** ACS 5-year (per-capita income, BA+, renter share; race and median home value
  for the Avenancio-León test).
- **Statistics:** median ratio; COD = 100 × mean|r - median| / median; PRD = mean(r) / weighted mean
  (sum AV / sum price); PRB = coefficient of ln(r) on log2 of the proxy above. IAAO targets: COD
  5-15 residential (tighter for newer homogeneous stock), PRD 0.98-1.03, |PRB| <= 0.05.

## Typical findings to expect

- A large urban residential roll can pass IAAO on COD, PRD and PRB with no neighbourhood bias once
  the sale filter is right — check before assuming a scandal.
- Commercial COD is commonly 25-35: the problem is dispersion, not a tilt toward large owners.
- A public-data tax-appeal screen tends to lose to the assessor (its COD worse than the office's)
  without new data on building condition.
