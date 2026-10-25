"""Parse what YOU copy from MahaRERA / IGR / Zapkey pages after solving their captcha yourself."""
from __future__ import annotations

import json
import re

from .. import ai
from ..models import ReraProject, Transaction
from .importers import _num

DATE = re.compile(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})|(\d{4})-(\d{2})-(\d{2})")


def _iso(m: re.Match) -> str:
    return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}" if m.group(1) else m.group(0)


def igr_rows_from_text(text: str, locality: str = "", project: str = "", rera_no: str = "") -> list[Transaction]:
    """Each line should contain a date, a consideration (₹), and an area (sq ft / sq m).
    Handles pasted Index-II tables and Zapkey/Square Yards transaction rows."""
    out = []
    for line in text.splitlines():
        d = DATE.search(line)
        if not d:
            continue
        rest = line.replace(d.group(0), " ")
        nums = [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*\.?\d*", rest) if len(x.replace(",", "")) >= 3]
        area_m = re.search(r"(\d[\d,]*\.?\d*)\s*(sq\.?\s*(?:ft|feet|mt|m)|sqft|sqm|sq\.?\s*meter)", rest, re.I)
        if not area_m:
            continue
        area = float(area_m.group(1).replace(",", ""))
        if re.match(r"sq\.?\s*(mt|m)|sqm|sq\.?\s*meter", area_m.group(2), re.I):
            area *= 10.7639
        vals = [n for n in nums if n >= 1_000_000 and abs(n - area) > 1]
        if not vals:
            continue
        out.append(Transaction(date=_iso(d), locality=locality, project_name=project, rera_no=rera_no,
                               area_sqft=round(area, 1), area_basis="carpet", agreement_value=max(vals) if len(vals) == 1 else vals[0]))
    return out


RERA_SYS = ("Extract a MahaRERA project page into JSON with keys: rera_no, name, builder, locality, "
            "status ('ongoing'|'completed'|'lapsed'|'revoked'|'unknown'), registered_on, original_completion (YYYY-MM), "
            "revised_completion (YYYY-MM), total_units (int|null), sold_units (int|null), complaints (int), "
            "litigation (bool). Use only what the text states; null/'' otherwise.")


def rera_from_text(text: str) -> ReraProject | None:
    d = None
    if ai.enabled():
        try:
            d = ai._json(ai._ask("researcher", RERA_SYS, text[:8000], 600))
        except Exception:
            d = None
    if not d or not d.get("rera_no"):
        m = re.search(r"\bP\d{11}\b", text)
        if not m:
            return None
        low = text.lower()
        d = {"rera_no": m.group(0), "name": "", "status": "lapsed" if "lapsed" in low else "revoked" if "revoked" in low else "unknown",
             "litigation": "litigation" in low and "no litigation" not in low}
    d = {k: v for k, v in d.items() if k in ReraProject.model_fields and v is not None}
    return ReraProject(**d)
