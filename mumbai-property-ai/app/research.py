"""Orchestrates one full property report."""
from __future__ import annotations

from . import ai, scoring, store
from .checklist import checklist
from .models import BuyerInputs, Listing, MarketParams, ReraProject, Transaction
from .returns import project_returns
from .valuation import quote_to_deal_gap, verify_price


def load():
    return ([Listing(**d) for d in store.all_("listings")],
            [Transaction(**d) for d in store.all_("transactions")],
            {d["rera_no"]: ReraProject(**d) for d in store.all_("rera")},
            {d["locality"].lower(): MarketParams(**d) for d in store.all_("market")})


def build_report(listing_id: str, buyer: BuyerInputs | None = None, use_ai: bool = True) -> dict | None:
    buyer = buyer or BuyerInputs()
    raw = store.get("listings", listing_id)
    if not raw:
        return None
    l = Listing(**raw)
    listings, txns, rera, mkts = load()
    mkt = mkts.get(l.locality.lower())
    proj = rera.get(l.rera_no) if l.rera_no else next(
        (p for p in rera.values() if l.project_name and p.name.lower() == l.project_name.lower()), None)
    price = buyer.negotiated_price or l.ask_price

    val = verify_price(l, txns, mkt, price)
    ret = project_returns(l, mkt, buyer, price)
    legal = scoring.rera_check(l, proj)
    n_active = sum(1 for x in listings if l.project_name and x.project_name.lower() == l.project_name.lower())
    inv = scoring.inventory(proj, n_active)
    sc = scoring.score(l, val, ret, legal, inv)
    rules_verdict = scoring.decide_rules(sc["total"], val, legal)

    facts = {"listing": l.model_dump(exclude={"raw_text"}), "price_check": val, "returns": ret,
             "legal": legal, "inventory": inv, "score": sc,
             "quote_to_deal": quote_to_deal_gap(listings, txns, l.project_name) if l.project_name else None,
             "market_assumptions": mkt.model_dump() if mkt else None}
    web = ai.web_notes(facts["listing"]) if use_ai else None
    if web:
        facts["web_notes_unverified"] = web
    analysis = ai.analyse(facts) if use_ai else ai.rule_analysis(facts)
    decision = ai.decide(facts, analysis, rules_verdict) if use_ai else {"decision": rules_verdict, "by": "rules"}
    return {**facts, "analysis_md": analysis, "decision": decision, "rules_verdict": rules_verdict,
            "checklist": checklist(l.status, bool(l.rera_no)),
            "ai": {"enabled": ai.enabled(), "models": ai.MODELS},
            "data_gaps": [g for g in (
                None if txns else "No registered-sale (IGR) data imported",
                None if proj else "No MahaRERA record for this project",
                None if mkt else "No market assumptions for this locality") if g]}


def rank(filters: dict) -> list[dict]:
    out = []
    for raw in store.all_("listings"):
        l = Listing(**raw)
        if filters.get("locality") and filters["locality"].lower() not in l.locality.lower():
            continue
        if filters.get("max_price") and l.ask_price > filters["max_price"]:
            continue
        if filters.get("min_price") and l.ask_price < filters["min_price"]:
            continue
        if filters.get("bhk") and l.bhk != filters["bhk"]:
            continue
        r = build_report(l.id, BuyerInputs(), use_ai=False)
        out.append({"id": l.id, "title": l.title or f"{l.bhk or ''} BHK {l.project_name}", "locality": l.locality,
                    "project": l.project_name, "source": l.source, "ask_price": l.ask_price,
                    "ask_vs_fair_pct": r["price_check"].get("ask_vs_fair_pct"),
                    "fair_value": r["price_check"].get("fair_value"),
                    "gross_yield_pct": r["returns"].get("gross_yield_pct"),
                    "base_irr_pct": r["returns"].get("scenarios", {}).get("base", {}).get("unlevered_irr_pct"),
                    "score": r["score"]["total"], "verdict": r["rules_verdict"],
                    "confidence": r["price_check"].get("confidence")})
    return sorted(out, key=lambda x: -x["score"])
