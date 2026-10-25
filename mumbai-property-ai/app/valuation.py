"""Price verification: compare the quoted price with *registered* (IGR Index-II) deals."""
from __future__ import annotations

from datetime import date, datetime
from statistics import median

from .models import Listing, MarketParams, Transaction

SALEABLE_PER_CARPET = 1.30      # typical Mumbai loading; override per project if known
BUILTUP_PER_CARPET = 1.15


def _to_carpet_area(area: float, basis: str) -> float:
    return {"carpet": area, "builtup": area / BUILTUP_PER_CARPET,
            "saleable": area / SALEABLE_PER_CARPET}[basis]


def _years_ago(d: str, today: date) -> float:
    try:
        return max((today - datetime.strptime(d[:10], "%Y-%m-%d").date()).days / 365.25, 0)
    except ValueError:
        return 5


def _wpercentile(pairs: list[tuple[float, float]], q: float) -> float:
    pairs = sorted(pairs)
    total = sum(w for _, w in pairs)
    acc = 0.0
    for v, w in pairs:
        acc += w
        if acc >= q * total:
            return v
    return pairs[-1][0]


def listing_carpet(l: Listing) -> float | None:
    if l.carpet_sqft:
        return l.carpet_sqft
    if l.saleable_sqft:
        return l.saleable_sqft / SALEABLE_PER_CARPET
    return None


def verify_price(l: Listing, txns: list[Transaction], mkt: MarketParams | None,
                 price: float | None = None, today: date | None = None) -> dict:
    """Returns fair-value range from registered comps (INR per carpet sqft, time-adjusted)."""
    today = today or date.today()
    price = price or l.ask_price
    carpet = listing_carpet(l)
    out: dict = {"ask_price": price, "carpet_sqft": carpet}
    if not carpet:
        return {**out, "confidence": "none", "warnings": ["No area stated: cannot verify price."]}
    ask_psf = price / carpet
    out["ask_psf_carpet"] = round(ask_psf)
    g = mkt.appreciation_base if mkt else 0.05

    def collect(rows: list[Transaction], max_years: float):
        res = []
        for t in rows:
            yrs = _years_ago(t.date, today)
            if yrs > max_years:
                continue
            ca = _to_carpet_area(t.area_sqft, t.area_basis)
            if not 0.7 * carpet <= ca <= 1.3 * carpet:
                continue
            psf = t.agreement_value / ca * (1 + g) ** yrs          # time-adjusted to today
            w = (1 / (1 + yrs)) * (1 - min(abs(ca - carpet) / carpet, 0.6))
            res.append((psf, w, t))
        return res

    proj = [t for t in txns if (l.rera_no and t.rera_no == l.rera_no) or
            (l.project_name and t.project_name.lower() == l.project_name.lower())]
    comps, tier = collect(proj, 2.0), "project"
    if len(comps) < 3:
        loc = [t for t in txns if t.locality.lower() == l.locality.lower()]
        comps, tier = collect(loc, 1.5), "locality"

    warnings: list[str] = []
    if not comps:
        out.update(confidence="none", comps_used=0, tier=None)
        warnings.append("No registered comparable deals found. Import Index-II data for this "
                        "project/locality before trusting any valuation.")
        out["warnings"] = warnings
        return out

    pairs = [(p, w) for p, w, _ in comps]
    med, lo, hi = _wpercentile(pairs, 0.5), _wpercentile(pairs, 0.25), _wpercentile(pairs, 0.75)
    n = len(comps)
    confidence = "high" if tier == "project" and n >= 5 else "medium" if n >= 3 else "low"
    gap = (price - med * carpet) / (med * carpet)
    out.update({
        "tier": tier, "comps_used": n, "confidence": confidence,
        "fair_psf_median": round(med), "fair_psf_low": round(lo), "fair_psf_high": round(hi),
        "fair_value": round(med * carpet), "fair_value_low": round(lo * carpet),
        "fair_value_high": round(hi * carpet),
        "ask_vs_fair_pct": round(gap * 100, 1),
        "raw_registered_psf": [round(t.agreement_value / _to_carpet_area(t.area_sqft, t.area_basis))
                               for _, _, t in comps][:12],
        "recent_deals": [{"date": t.date, "project": t.project_name,
                          "area_sqft": t.area_sqft, "basis": t.area_basis,
                          "agreement_value": round(t.agreement_value), "doc_no": t.doc_no}
                         for _, _, t in sorted(comps, key=lambda c: c[2].date, reverse=True)[:8]],
        # Negotiation anchors
        "target_price": round(lo * carpet + 0.5 * (med - lo) * carpet),
        "walk_away_price": round(hi * carpet),
    })
    if mkt and mkt.ready_reckoner_psf:
        rr_carpet = mkt.ready_reckoner_psf * BUILTUP_PER_CARPET
        if med < rr_carpet * 0.9:
            warnings.append("Registered deals sit below Ready Reckoner: check area basis/data quality.")
    if gap > 0.10:
        warnings.append(f"Quote is {gap*100:.0f}% above registered-deal fair value.")
    if tier == "locality":
        warnings.append("Comps are locality-level, not same-project: treat as an indication.")
    out["warnings"] = warnings
    return out


def quote_to_deal_gap(listings: list[Listing], txns: list[Transaction], project: str,
                      today: date | None = None) -> dict | None:
    """How far below asking do deals actually close in this project?"""
    today = today or date.today()
    asks = [l.ask_price / c for l in listings
            if l.project_name.lower() == project.lower() and (c := listing_carpet(l))]
    deals = [t.agreement_value / _to_carpet_area(t.area_sqft, t.area_basis) for t in txns
             if t.project_name.lower() == project.lower() and _years_ago(t.date, today) <= 1.0]
    if len(asks) < 2 or len(deals) < 2:
        return None
    a, d = median(asks), median(deals)
    return {"median_ask_psf": round(a), "median_registered_psf": round(d),
            "typical_discount_pct": round((a - d) / a * 100, 1), "n_asks": len(asks), "n_deals": len(deals)}
