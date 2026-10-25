"""Turn a pasted post (Facebook / Instagram / WhatsApp / portal text) into a Listing.
Haiku does it when a key is present; otherwise regex rules."""
from __future__ import annotations

import re

from .. import ai
from ..models import Listing

LOCALITIES = ["Andheri West", "Andheri East", "Bandra West", "Bandra East", "Powai", "Goregaon East",
              "Goregaon West", "Malad West", "Malad East", "Kandivali East", "Kandivali West",
              "Borivali West", "Borivali East", "Chembur", "Mulund West", "Mulund East", "Worli",
              "Lower Parel", "Dadar", "Prabhadevi", "Santacruz", "Vile Parle", "Juhu", "Versova",
              "Ghatkopar", "Vikhroli", "Kurla", "Wadala", "Mahim", "Colaba", "Malabar Hill",
              "Parel", "Byculla", "Jogeshwari", "Dahisar", "Bhandup", "Kanjurmarg"]
PRICE = re.compile(r"(?:₹|rs\.?|inr)?\s*(\d+(?:[.,]\d+)?)\s*(cr(?:ore)?s?|crs?|lakhs?|lacs?|l\b|k\b)?", re.I)


def parse_price(text: str) -> float | None:
    for m in re.finditer(r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(cr(?:ore)?s?|lakhs?|lacs?)\b", text, re.I):
        n, unit = float(m.group(1)), m.group(2).lower()
        return n * (1e7 if unit.startswith("cr") else 1e5)
    m = re.search(r"(?:₹|rs\.?|inr)\s*([\d,]{7,})", text, re.I)
    return float(m.group(1).replace(",", "")) if m else None


def rules_extract(text: str) -> dict:
    t = text.replace(" ", " ")
    d: dict = {}
    d["ask_price"] = parse_price(t) or 0
    m = re.search(r"(\d(?:\.\d)?)\s*bhk", t, re.I)
    d["bhk"] = float(m.group(1)) if m else None
    for kind, key in (("carpet", "carpet_sqft"), (r"saleable|super\s*built\s*up|sba|built\s*up", "saleable_sqft")):
        m = (re.search(rf"(\d{{3,5}})\s*(?:sq\.?\s*ft|sqft|sft)\.?\s*(?:\(?\s*)?(?:{kind})", t, re.I)
             or re.search(rf"(?:{kind})\s*(?:area)?\s*[:\-]?\s*(\d{{3,5}})", t, re.I))
        if m:
            d[key] = float(m.group(1))
    if "carpet_sqft" not in d and "saleable_sqft" not in d:
        m = re.search(r"(\d{3,5})\s*(?:sq\.?\s*ft|sqft|sft)", t, re.I)
        if m:
            d["saleable_sqft"] = float(m.group(1))     # unlabeled area: assume the looser basis
    for loc in sorted(LOCALITIES, key=len, reverse=True):
        if loc.lower() in t.lower():
            d["locality"] = loc
            break
    m = re.search(r"\bP\d{11}\b", t)
    d["rera_no"] = m.group(0) if m else ""
    low = t.lower()
    d["status"] = ("under_construction" if re.search(r"under construction|possession (?:in|by)|new launch|pre-?launch", low)
                   else "ready" if re.search(r"ready to move|ready possession|resale|\boc\b received", low) else "unknown")
    if re.search(r"\boc (?:received|available|ready)|with oc", low):
        d["oc_received"] = True
    d["furnishing"] = ("furnished" if re.search(r"fully furnished|\bfurnished\b", low) and "semi" not in low and "unfurnished" not in low
                       else "semi" if "semi" in low else "unfurnished" if "unfurnished" in low else "unknown")
    m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s*floor(?:\s*(?:of|/)\s*(\d{1,2}))?", low)
    if m:
        d["floor"] = int(m.group(1))
        d["total_floors"] = int(m.group(2)) if m.group(2) else None
    return d


def to_listing(text: str, source: str = "manual", url: str = "") -> Listing:
    data, how = ai.llm_extract(text), "llm"
    if not data or not data.get("ask_price"):
        data, how = rules_extract(text), "rules"
    clean = {k: v for k, v in data.items() if k in Listing.model_fields and v not in (None, "")}
    return Listing(**clean, source=source, url=url, raw_text=text[:4000], extraction=how)
