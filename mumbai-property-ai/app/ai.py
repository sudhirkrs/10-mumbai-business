"""Three-role model pipeline:
  researcher (Haiku 5.5)  : extracts listings from messy text, gathers web notes
  analyst    (Sonnet 5.5) : writes the buy/no-buy analysis from the verified numbers
  decider    (Opus 5.5)   : makes the final call, constrained by the numeric evidence
All three degrade to rule-based output when ANTHROPIC_API_KEY is absent."""
from __future__ import annotations

import json
import os
import re

MODELS = {
    "researcher": os.environ.get("PROPAI_RESEARCH_MODEL", "claude-haiku-5-5"),
    "analyst": os.environ.get("PROPAI_ANALYST_MODEL", "claude-sonnet-5-5"),
    "decider": os.environ.get("PROPAI_DECIDER_MODEL", "claude-opus-5-5"),
}


def enabled() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _client():
    import anthropic
    return anthropic.Anthropic()


def _ask(role: str, system: str, user: str, max_tokens: int = 1500, tools: list | None = None) -> str:
    kw = {"tools": tools} if tools else {}
    msg = _client().messages.create(model=MODELS[role], max_tokens=max_tokens, system=system,
                                    messages=[{"role": "user", "content": user}], **kw)
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()


def _json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {}


# ---------- Researcher (Haiku) ----------
EXTRACT_SYS = (
    "You extract a Mumbai property listing from a pasted portal/Facebook/Instagram/WhatsApp post. "
    "Return ONLY JSON with keys: title, locality, project_name, builder, rera_no, bhk (number), "
    "carpet_sqft, saleable_sqft, ask_price (INR as a number; 1 Cr=10000000, 1 lakh=100000), floor, "
    "total_floors, age_years, status ('ready'|'under_construction'|'unknown'), oc_received (bool|null), "
    "possession_date (YYYY-MM or ''), furnishing ('unfurnished'|'semi'|'furnished'|'unknown'), "
    "parking (int|null), expected_rent (INR/month|null). Use null/'' for anything not stated. Never guess."
)


def llm_extract(text: str) -> dict | None:
    if not enabled():
        return None
    try:
        return _json(_ask("researcher", EXTRACT_SYS, text[:6000], 700))
    except Exception:
        return None


def web_notes(listing: dict) -> str | None:
    """Optional: Haiku + server-side web search for project/builder reputation. Unverified notes."""
    if not enabled() or os.environ.get("PROPAI_WEB_RESEARCH") != "1":
        return None
    q = f"{listing.get('project_name')} {listing.get('builder')} {listing.get('locality')} Mumbai: " \
        "possession delays, RERA complaints, reviews, resale prices. Cite source URLs. Be brief."
    try:
        return _ask("researcher", "You are a careful property researcher. Report only what sources say; "
                    "mark anything uncertain.", q, 900,
                    tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}])
    except Exception:
        return None


# ---------- Analyst (Sonnet) ----------
ANALYST_SYS = (
    "You are a Mumbai real-estate buy-side analyst. Using ONLY the JSON facts provided, write: "
    "(1) 'Why it could be a good buy' (3-5 bullets), (2) 'Why it might not be' (3-5 bullets), "
    "(3) 'Price reality': quoted vs registered deals, with the numbers, "
    "(4) 'Returns': rent, yield, appreciation scenarios. Quote figures exactly from the facts; "
    "never invent numbers, comps, or legal conclusions. Say 'not available' when data is missing. "
    "Plain, direct, concise. Markdown."
)


def analyse(facts: dict) -> str:
    if enabled():
        try:
            return _ask("analyst", ANALYST_SYS, json.dumps(facts, default=str), 1400)
        except Exception:
            pass
    return rule_analysis(facts)


def rule_analysis(f: dict) -> str:
    v, r = f["price_check"], f["returns"]
    good, bad = [], []
    gap = v.get("ask_vs_fair_pct")
    if gap is not None:
        (good if gap <= 0 else bad).append(
            f"Quote is {abs(gap)}% {'below' if gap <= 0 else 'above'} registered-deal fair value "
            f"(₹{v['fair_value']:,} from {v['comps_used']} {v['tier']}-level deals).")
    else:
        bad.append("Price cannot be verified: no registered comps imported.")
    if r.get("gross_yield_pct"):
        (good if r["net_yield_pct"] >= 2.5 else bad).append(
            f"Gross yield {r['gross_yield_pct']}%, net {r['net_yield_pct']}% on all-in cost.")
    base = r.get("scenarios", {}).get("base")
    if base:
        (good if (base["unlevered_irr_pct"] or 0) > r["alt_return_pct"] else bad).append(
            f"Base-case unlevered IRR {base['unlevered_irr_pct']}% over {r['hold_years']}y vs "
            f"{r['alt_return_pct']:.0f}% safe-return benchmark.")
    for fl in f["legal"]["flags"]:
        bad.append(fl["text"])
    for w in v.get("warnings", []):
        bad.append(w)
    fmt = lambda xs: "\n".join(f"- {x}" for x in xs) or "- none identified from available data"
    return f"**Why it could be a good buy**\n{fmt(good)}\n\n**Why it might not be**\n{fmt(bad)}"


# ---------- Decider (Opus) ----------
DECIDER_SYS = (
    "You are the final decision-maker for a Mumbai home purchase. You get verified numeric facts, "
    "an analyst note and a rule-based verdict. Decide one of: STRONG BUY, BUY AT TARGET PRICE, "
    "NEGOTIATE HARD, VERIFY FIRST, PASS, AVOID. You may not upgrade a rule-based AVOID, and must not "
    "rate STRONG BUY when price confidence is low/none. Return ONLY JSON: "
    '{"decision": str, "max_price_inr": number|null, "rationale": str (<=80 words), '
    '"conditions": [str,...] (things that must be true before paying)}.'
)
ORDER = ["AVOID", "PASS", "VERIFY FIRST", "NEGOTIATE HARD", "BUY AT TARGET PRICE", "STRONG BUY"]


def decide(facts: dict, analysis: str, rules_verdict: str) -> dict:
    fallback = {"decision": rules_verdict, "max_price_inr": facts["price_check"].get("walk_away_price"),
                "rationale": "Rule-based verdict (AI decider not configured).",
                "conditions": [], "by": "rules"}
    if not enabled():
        return fallback
    try:
        out = _json(_ask("decider", DECIDER_SYS, json.dumps(
            {"facts": facts, "analyst_note": analysis, "rules_verdict": rules_verdict}, default=str), 700))
        d = out.get("decision", rules_verdict)
        if d not in ORDER:
            d = rules_verdict
        if rules_verdict == "AVOID":
            d = "AVOID"
        if facts["price_check"].get("confidence") in (None, "none", "low") and d == "STRONG BUY":
            d = "VERIFY FIRST"
        return {"decision": d, "max_price_inr": out.get("max_price_inr"),
                "rationale": out.get("rationale", ""), "conditions": out.get("conditions", []),
                "by": MODELS["decider"]}
    except Exception:
        return fallback


# ---------- Area research (Haiku + live web search) ----------
AREA_SYS = ("You are a Mumbai property researcher with web search. Find CURRENT information and report only what "
            "sources state. Return ONLY JSON: {\"price_trend\": str, \"rent_trend\": str, "
            "\"active_projects\": [{\"name\": str, \"builder\": str, \"indicative_price\": str, \"url\": str, \"note\": str}], "
            "\"listing_snapshots\": [{\"title\": str, \"price\": str, \"url\": str}], "
            "\"risks\": [str], \"gaps\": [str]}. Every item needs a source url. Put anything you could not find in gaps. "
            "These are asking prices/claims, not registered transactions: say so.")


def area_research(locality: str, budget: str = "") -> dict:
    if not enabled():
        return {"error": "ANTHROPIC_API_KEY not set: live web research is unavailable."}
    q = (f"{locality}, Mumbai: current resale and new-launch 1-3 BHK prices per sq ft, active RERA-registered projects, "
         f"recent rents, builder delays or complaints, notable news in the last 6 months. {budget}")
    try:
        txt = _ask("researcher", AREA_SYS, q, 2500,
                   tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}])
        return _json(txt) or {"error": "No structured result", "raw": txt[:1500]}
    except Exception as e:
        return {"error": f"Research failed: {type(e).__name__}"}
