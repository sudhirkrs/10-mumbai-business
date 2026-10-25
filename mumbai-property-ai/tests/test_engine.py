import os, tempfile
os.environ["PROPAI_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
os.environ.pop("ANTHROPIC_API_KEY", None)

from fastapi.testclient import TestClient
from app import costs, demo, store
from app.connectors import importers, text_ingest
from app.main import app
from app.returns import irr

c = TestClient(app)


def test_costs_mumbai():
    r = costs.acquisition_cost(1e7, "ready")
    assert r["items"]["stamp_duty_incl_metro_cess"] == 600_000
    assert r["items"]["registration"] == 30_000          # capped
    assert costs.acquisition_cost(1e7, "under_construction")["items"]["gst"] == 500_000


def test_irr():
    assert abs(irr([-100] + [0] * 11 + [110]) - 0.10) < 0.005


def test_text_rules():
    d = text_ingest.rules_extract("Spacious 2BHK 650 sq ft carpet in Powai, Sample Residency, 2.1 Cr, "
                                  "RERA P51800000002, ready to move, 8th floor of 22")
    assert d["ask_price"] == 2.1e7 and d["bhk"] == 2 and d["carpet_sqft"] == 650
    assert d["locality"] == "Powai" and d["rera_no"] == "P51800000002" and d["floor"] == 8
    assert text_ingest.parse_price("Rs. 85 lakh negotiable") == 8.5e6


def test_igr_import_aliases():
    csv = b"Registration Date,Consideration,Carpet Area,Project,Location\n2026-05-01,\"2,00,00,000\",600,Demo Heights,Andheri West\n"
    t = importers.transactions_from(csv, "x.csv")
    assert len(t) == 1 and t[0].area_sqft == 600


def test_end_to_end():
    demo.seed()
    rows = c.get("/api/listings").json()
    assert rows and rows == sorted(rows, key=lambda r: -r["score"])
    # lapsed + litigation project must never be a buy
    bad = [r for r in rows if r["project"] == "Fictional Park"]
    assert all(r["verdict"] == "AVOID" for r in bad)
    rep = c.post(f"/api/listings/{rows[0]['id']}/report", json={}).json()
    assert rep["price_check"]["comps_used"] >= 3 and rep["returns"]["scenarios"]["base"]
    assert rep["decision"]["by"] == "rules" and rep["checklist"]


def test_paste_endpoint():
    r = c.post("/api/ingest/text", json={"text": "1BHK 450 sqft carpet Chembur Mock Gardens 1.3 Cr", "source": "instagram"})
    assert r.status_code == 200 and r.json()["source"] == "instagram"
    assert c.post("/api/ingest/text", json={"text": "nice flat"}).status_code == 422
