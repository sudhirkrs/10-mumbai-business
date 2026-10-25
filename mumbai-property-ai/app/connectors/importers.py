"""Compliant data paths: you export/download from the source, we normalise.
 - portals: CSV/JSON export (or a licensed data feed) of listings
 - IGR Maharashtra: Index-II registered-sale CSV (igrmaharashtra.gov.in, captcha-gated, so downloaded by you)
 - MahaRERA: project JSON/CSV (maharerait.maharashtra.gov.in, captcha-gated)"""
from __future__ import annotations

import csv
import io
import json

from ..models import Listing, ReraProject, Transaction

ALIASES = {
    "ask_price": ["price", "asking_price", "ask", "amount", "quoted_price"],
    "carpet_sqft": ["carpet", "carpet_area", "carpet_area_sqft"],
    "saleable_sqft": ["saleable", "super_builtup", "super_built_up_area", "area_sqft", "built_up_area"],
    "project_name": ["project", "society", "building"],
    "locality": ["location", "area", "micro_market", "village"],
    "agreement_value": ["consideration", "consideration_amount", "value", "market_value", "sale_value"],
    "date": ["registration_date", "reg_date", "date_of_registration", "dateofregistration"],
    "area_sqft": ["area", "carpet_area", "built_up_area", "area_in_sqft", "carpet_sqft"],
    "doc_no": ["document_no", "doc_number", "document_number", "docno"],
    "rera_no": ["rera", "rera_number", "registration_no", "maharera_no"],
    "name": ["project_name", "title"],
}


def _norm(row: dict) -> dict:
    out = {}
    for k, v in row.items():
        k2 = str(k).strip().lower().replace(" ", "_").replace("-", "_")
        out[k2] = v.strip() if isinstance(v, str) else v
    for canon, alts in ALIASES.items():
        if canon not in out or out[canon] in ("", None):
            for a in alts:
                if out.get(a) not in (None, ""):
                    out[canon] = out[a]
                    break
    return out


def _num(v) -> float | None:
    if v in (None, ""):
        return None
    try:
        return float(str(v).replace(",", "").replace("₹", "").strip())
    except ValueError:
        return None


def rows(content: bytes, filename: str) -> list[dict]:
    text = content.decode("utf-8-sig")
    if filename.lower().endswith(".json"):
        data = json.loads(text)
        data = data if isinstance(data, list) else data.get("items", [])
        return [_norm(r) for r in data]
    return [_norm(r) for r in csv.DictReader(io.StringIO(text))]


def listings_from(content: bytes, filename: str, source: str = "other") -> list[Listing]:
    out = []
    for r in rows(content, filename):
        price = _num(r.get("ask_price"))
        if not price:
            continue
        out.append(Listing(
            source=r.get("source") or source, url=r.get("url", ""), title=r.get("title", ""),
            locality=r.get("locality", ""), project_name=r.get("project_name", ""),
            builder=r.get("builder", ""), rera_no=r.get("rera_no", ""), bhk=_num(r.get("bhk")),
            carpet_sqft=_num(r.get("carpet_sqft")), saleable_sqft=_num(r.get("saleable_sqft")),
            ask_price=price, floor=int(_num(r.get("floor")) or 0) or None,
            age_years=_num(r.get("age_years")), status=r.get("status") or "unknown",
            oc_received={"true": True, "false": False, "yes": True, "no": False}.get(str(r.get("oc_received", "")).lower()),
            possession_date=r.get("possession_date", ""), furnishing=r.get("furnishing") or "unknown",
            expected_rent=_num(r.get("expected_rent")), posted_date=r.get("posted_date", ""),
            extraction="import"))
    return out


def transactions_from(content: bytes, filename: str) -> list[Transaction]:
    out = []
    for r in rows(content, filename):
        area, val = _num(r.get("area_sqft")), _num(r.get("agreement_value"))
        if not (area and val and r.get("date")):
            continue
        out.append(Transaction(
            date=str(r["date"])[:10], locality=r.get("locality", ""), project_name=r.get("project_name", ""),
            rera_no=r.get("rera_no", ""), area_sqft=area,
            area_basis=r.get("area_basis") or "carpet", agreement_value=val,
            ready_reckoner_psf=_num(r.get("ready_reckoner_psf")), doc_no=r.get("doc_no", ""),
            kind=r.get("kind") or "resale"))
    return out


def rera_from(content: bytes, filename: str) -> list[ReraProject]:
    out = []
    for r in rows(content, filename):
        if not r.get("rera_no"):
            continue
        unsold = r.get("unsold_by_bhk") or {}
        if isinstance(unsold, str):
            try:
                unsold = json.loads(unsold)
            except ValueError:
                unsold = {}
        out.append(ReraProject(
            rera_no=r["rera_no"], name=r.get("name", ""), builder=r.get("builder", ""),
            locality=r.get("locality", ""), status=r.get("status") or "unknown",
            registered_on=r.get("registered_on", ""), original_completion=r.get("original_completion", ""),
            revised_completion=r.get("revised_completion", ""),
            total_units=int(_num(r.get("total_units")) or 0) or None,
            sold_units=None if _num(r.get("sold_units")) is None else int(_num(r.get("sold_units"))),
            unsold_by_bhk=unsold, complaints=int(_num(r.get("complaints")) or 0),
            litigation=str(r.get("litigation", "")).lower() in ("true", "yes", "1"),
            last_updated=r.get("last_updated", "")))
    return out
