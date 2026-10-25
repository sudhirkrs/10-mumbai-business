"""Acquisition cost for a Mumbai purchase. Rates are parameters: verify against current
Maharashtra notifications before relying on them."""
from __future__ import annotations

STAMP_DUTY = 0.05          # state stamp duty, Mumbai
METRO_CESS = 0.01          # 1% surcharge in BMC area (stamp duty total 6%)
REGISTRATION = 0.01
REGISTRATION_CAP = 30_000
GST_UC = 0.05              # under-construction, non-affordable (no ITC). 1% if affordable.
TDS_PCT = 0.01             # buyer deducts on consideration > 50L (not an extra cost; cash-flow timing)
BROKERAGE = 0.01
LEGAL = 40_000
SOCIETY_TRANSFER = 25_000  # resale; varies widely by society


def acquisition_cost(price: float, status: str, woman_buyer: bool = False,
                     resale_brokerage: bool = True) -> dict:
    stamp = price * (STAMP_DUTY + METRO_CESS - (0.01 if woman_buyer else 0))
    reg = min(price * REGISTRATION, REGISTRATION_CAP)
    gst = price * GST_UC if status == "under_construction" else 0.0
    brokerage = price * BROKERAGE if resale_brokerage else 0.0
    transfer = SOCIETY_TRANSFER if status == "ready" else 0.0
    items = {
        "stamp_duty_incl_metro_cess": round(stamp),
        "registration": round(reg),
        "gst": round(gst),
        "brokerage": round(brokerage),
        "legal_and_due_diligence": LEGAL,
        "society_transfer_and_deposit": transfer,
    }
    total_extra = sum(items.values())
    return {"price": round(price), "items": items, "total_extra": round(total_extra),
            "all_in": round(price + total_extra), "extra_pct": round(total_extra / price * 100, 2)}


def emi(principal: float, annual_rate: float, years: int) -> float:
    r = annual_rate / 12
    n = years * 12
    if r == 0:
        return principal / n
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)
