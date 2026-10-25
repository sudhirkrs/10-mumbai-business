"""Rental yield, appreciation scenarios, and levered IRR."""
from __future__ import annotations

from .costs import acquisition_cost, emi
from .models import BuyerInputs, Listing, MarketParams
from .valuation import listing_carpet

LTCG_RATE = 0.125          # long-term capital gains on property, no indexation (verify current law)
SELL_COST = 0.02           # brokerage + legal on exit
OPEX_PCT_OF_RENT = 0.12    # property tax, repairs, non-occupancy society charges
VACANCY_MONTHS = 1.0
FURNISH_PREMIUM = {"unfurnished": 1.0, "semi": 1.08, "furnished": 1.18, "unknown": 1.0}


def irr(cashflows: list[float]) -> float | None:
    """Annualised IRR from monthly flows, via bisection."""
    def npv(r):
        return sum(cf / (1 + r) ** (i / 12) for i, cf in enumerate(cashflows))
    lo, hi = -0.9, 2.0
    if npv(lo) * npv(hi) > 0:
        return None
    for _ in range(100):
        mid = (lo + hi) / 2
        if npv(lo) * npv(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def expected_rent(l: Listing, mkt: MarketParams | None, custom: float | None) -> tuple[float | None, str]:
    if custom:
        return custom, "user input"
    if l.expected_rent:
        return l.expected_rent, "stated by lister"
    carpet = listing_carpet(l)
    if mkt and carpet:
        return round(mkt.rent_psf_month * carpet * FURNISH_PREMIUM[l.furnishing]), "market assumption"
    return None, "unavailable"


def project_returns(l: Listing, mkt: MarketParams | None, b: BuyerInputs, price: float) -> dict:
    cost = acquisition_cost(price, l.status, b.is_woman_buyer)
    rent, rent_src = expected_rent(l, mkt, b.custom_rent)
    out: dict = {"cost": cost, "rent_source": rent_src}
    if not rent or not mkt:
        out["warnings"] = ["Rent/appreciation assumptions missing for this locality."]
        return out

    gross = rent * 12
    net = rent * (12 - VACANCY_MONTHS) * (1 - OPEX_PCT_OF_RENT)
    out.update({
        "expected_rent_month": round(rent),
        "gross_yield_pct": round(gross / price * 100, 2),
        "net_yield_pct": round(net / cost["all_in"] * 100, 2),
        "rent_note": "Rent starts at possession for under-construction homes." if l.status == "under_construction" else "",
    })

    loan = price * (1 - b.down_payment_pct)
    pay = emi(loan, b.loan_rate, b.loan_years)
    equity = cost["all_in"] - loan
    out["financing"] = {"loan": round(loan), "emi": round(pay), "equity_needed": round(equity),
                        "rent_covers_emi_pct": round(rent / pay * 100, 1)}

    scenarios = {}
    for name, g in (("bear", mkt.appreciation_bear), ("base", mkt.appreciation_base),
                    ("bull", mkt.appreciation_bull)):
        years = b.hold_years
        sale = price * (1 + g) ** years
        gain = max(sale - price, 0)
        net_sale = sale * (1 - SELL_COST) - gain * LTCG_RATE
        months = years * 12
        n = b.loan_years * 12
        r = b.loan_rate / 12
        bal = loan
        flows = [-equity]
        for m in range(1, months + 1):
            if m <= n:
                bal = bal * (1 + r) - pay
            rent_m = rent * (1 + mkt.rent_growth) ** ((m - 1) // 12)
            cf = rent_m * (1 - OPEX_PCT_OF_RENT) * (12 - VACANCY_MONTHS) / 12
            if m <= n:
                cf -= pay
            flows.append(cf)
        flows[-1] += net_sale - max(bal, 0)
        rate = irr(flows)
        unlev = irr([-cost["all_in"]] + [rent * (1 + mkt.rent_growth) ** ((m - 1) // 12) *
                    (1 - OPEX_PCT_OF_RENT) * (12 - VACANCY_MONTHS) / 12 for m in range(1, months + 1)][:-1]
                    + [rent * (1 - OPEX_PCT_OF_RENT) * (12 - VACANCY_MONTHS) / 12 + net_sale])
        scenarios[name] = {"cagr_pct": round(g * 100, 1), "value_at_exit": round(sale),
                           "net_sale_after_tax_costs": round(net_sale),
                           "levered_irr_pct": None if rate is None else round(rate * 100, 1),
                           "unlevered_irr_pct": None if unlev is None else round(unlev * 100, 1)}
    out["scenarios"] = scenarios
    out["hold_years"] = b.hold_years
    out["beats_alt_in_base"] = (scenarios["base"]["unlevered_irr_pct"] or -99) > b.alt_return * 100
    out["alt_return_pct"] = b.alt_return * 100
    return out
