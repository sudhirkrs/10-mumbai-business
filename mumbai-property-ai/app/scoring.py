"""Buy score (0-100) and red flags, from the numbers only."""
from __future__ import annotations

from datetime import date

from .models import Listing, ReraProject


def _months_between(a: str, b: str) -> int | None:
    try:
        ya, ma = map(int, a[:7].split("-"))
        yb, mb = map(int, b[:7].split("-"))
        return (yb - ya) * 12 + (mb - ma)
    except ValueError:
        return None


def rera_check(l: Listing, p: ReraProject | None) -> dict:
    flags: list[dict] = []
    if l.status == "under_construction" and not l.rera_no:
        flags.append({"sev": "high", "text": "Under-construction listing with no RERA number. Do not proceed without one."})
    if l.rera_no and not p:
        flags.append({"sev": "medium", "text": f"RERA no. {l.rera_no} not in your imported MahaRERA data: verify on maharerait.maharashtra.gov.in."})
    if p:
        if p.status in ("lapsed", "revoked"):
            flags.append({"sev": "high", "text": f"RERA registration is {p.status}."})
        if p.litigation:
            flags.append({"sev": "high", "text": "Litigation is recorded against the project."})
        if p.complaints >= 3:
            flags.append({"sev": "medium", "text": f"{p.complaints} complaints filed against this project on MahaRERA."})
        d = _months_between(p.original_completion, p.revised_completion) if p.revised_completion else None
        if d and d > 12:
            flags.append({"sev": "medium", "text": f"Possession already pushed back {d} months vs the original RERA date."})
        if p.builder and l.builder and p.builder.lower() != l.builder.lower():
            flags.append({"sev": "medium", "text": "Builder on the listing differs from the RERA-registered promoter."})
    return {"project": p.model_dump() if p else None, "flags": flags}


def inventory(p: ReraProject | None, active_listings: int) -> dict | None:
    if not p or p.total_units is None or p.sold_units is None:
        return {"active_listings": active_listings} if active_listings else None
    unsold = p.total_units - p.sold_units
    return {"total_units": p.total_units, "sold_units": p.sold_units, "unsold_units": unsold,
            "sold_pct": round(p.sold_units / p.total_units * 100) if p.total_units else None,
            "unsold_by_bhk": p.unsold_by_bhk, "active_resale_listings": active_listings,
            "as_of": p.last_updated}


def score(l: Listing, val: dict, ret: dict, rera: dict, inv: dict | None) -> dict:
    pts: dict[str, float] = {}
    gap = val.get("ask_vs_fair_pct")
    if gap is None:
        pts["price_vs_registered"] = 8              # unknown: neutral-low
    else:
        pts["price_vs_registered"] = max(0, min(35, 35 - (gap + 10) * 1.5)) if gap > -10 else 35
    n_high = sum(f["sev"] == "high" for f in rera["flags"])
    n_med = sum(f["sev"] == "medium" for f in rera["flags"])
    pts["legal_rera"] = max(0, 25 - 12 * n_high - 5 * n_med)
    gy = ret.get("net_yield_pct")
    pts["rental_yield"] = 0 if gy is None else min(15, gy / 3.0 * 15)
    base = ret.get("scenarios", {}).get("base", {}).get("unlevered_irr_pct")
    pts["total_return"] = 0 if base is None else max(0, min(15, (base - 4) / 6 * 15))
    liq = 5.0
    if inv and inv.get("unsold_units") is not None and inv.get("total_units"):
        liq = 10 * (1 - min(inv["unsold_units"] / inv["total_units"], 1)) + 0
    pts["liquidity_inventory"] = min(10, liq)
    total = round(sum(pts.values()))
    conf = val.get("confidence", "none")
    if conf in ("none", "low"):
        total = min(total, 65)                       # cannot be a top pick on thin price evidence
    return {"total": total, "parts": {k: round(v, 1) for k, v in pts.items()}}


def decide_rules(total: int, val: dict, rera: dict) -> str:
    high = any(f["sev"] == "high" for f in rera["flags"])
    gap = val.get("ask_vs_fair_pct")
    if high:
        return "AVOID"
    if val.get("confidence") in ("none", "low"):
        return "VERIFY FIRST"
    if gap is not None and gap > 12:
        return "NEGOTIATE HARD"
    if total >= 75 and (gap is None or gap <= 3):
        return "STRONG BUY"
    if total >= 60:
        return "BUY AT TARGET PRICE"
    return "PASS"
