"""DEMO DATA ONLY. Fictional projects and invented numbers so the app runs offline.
Replace with real Index-II / MahaRERA / listing imports. Market assumptions are placeholders."""
from __future__ import annotations

import random
from datetime import date, timedelta

from . import store

MARKET = [  # locality, RR psf, rent psf/month (carpet), bear, base, bull   (PLACEHOLDERS)
    ("Andheri West", 20000, 95, .02, .05, .08), ("Powai", 15000, 85, .02, .055, .085),
    ("Goregaon East", 13500, 75, .02, .05, .08), ("Chembur", 15000, 80, .02, .05, .08),
    ("Malad West", 12500, 70, .02, .05, .08), ("Borivali West", 11000, 65, .02, .045, .07),
    ("Mulund West", 12000, 68, .02, .045, .07), ("Kandivali East", 11000, 62, .02, .045, .07),
]
PROJECTS = [  # name, locality, rera, builder, base carpet psf, units, sold, status, complaints, litig
    ("Demo Heights", "Andheri West", "P51800000001", "Demo Builders", 38000, 240, 200, "ongoing", 0, False),
    ("Sample Residency", "Powai", "P51800000002", "Sample Realty", 30000, 300, 290, "completed", 1, False),
    ("Test Towers", "Goregaon East", "P51800000003", "Test Corp", 26000, 180, 90, "ongoing", 5, False),
    ("Mock Gardens", "Chembur", "P51800000004", "Mock Infra", 29000, 120, 118, "completed", 0, False),
    ("Fictional Park", "Malad West", "P51800000005", "Fiction Homes", 24000, 400, 310, "lapsed", 7, True),
]


def seed() -> dict:
    rnd = random.Random(7)
    for c in ("listings", "transactions", "rera", "market"):
        store.clear(c)
    for loc, rr, rent, b, m, u in MARKET:
        store.put("market", dict(locality=loc, ready_reckoner_psf=rr, rent_psf_month=rent,
                                 appreciation_bear=b, appreciation_base=m, appreciation_bull=u,
                                 note="PLACEHOLDER assumption"), loc)
    today = date.today()
    for name, loc, rera, builder, psf, units, sold, status, comp, lit in PROJECTS:
        store.put("rera", dict(rera_no=rera, name=name, builder=builder, locality=loc, status=status,
                  original_completion="2025-12", revised_completion="2027-06" if status == "ongoing" else "2025-12",
                  total_units=units, sold_units=sold, unsold_by_bhk={"1": (units - sold) // 3, "2": (units - sold) // 2, "3": (units - sold) // 6},
                  complaints=comp, litigation=lit, last_updated=str(today)), rera)
        for i in range(14):                       # registered deals, ~8% below typical asks
            carpet = rnd.choice([450, 580, 650, 800, 950])
            d = today - timedelta(days=rnd.randint(10, 540))
            p = psf * (1 + rnd.uniform(-0.06, 0.06)) * (1 - 0.02 * (d < today - timedelta(days=360)))
            store.put("transactions", dict(date=str(d), locality=loc, project_name=name, rera_no=rera,
                      area_sqft=carpet, area_basis="carpet", agreement_value=round(p * carpet, -3),
                      doc_no=f"DEMO-{name[:3].upper()}-{i:03d}"))
        for j in range(3):
            carpet = rnd.choice([450, 580, 650, 800])
            ask = psf * carpet * rnd.choice([1.00, 1.08, 1.14, 0.96]) 
            store.put("listings", dict(source=rnd.choice(["magicbricks", "99acres", "facebook", "broker"]),
                      title=f"{ {450:1,580:2,650:2,800:3}[carpet] } BHK in {name}", locality=loc,
                      project_name=name, builder=builder, rera_no=rera, bhk={450: 1, 580: 2, 650: 2, 800: 3}[carpet],
                      carpet_sqft=carpet, ask_price=round(ask, -4),
                      status="ready" if status == "completed" else "under_construction",
                      oc_received=True if status == "completed" else None, furnishing="unfurnished",
                      floor=rnd.randint(3, 20), extraction="import"))
    return {"market": len(MARKET), "projects": len(PROJECTS)}
