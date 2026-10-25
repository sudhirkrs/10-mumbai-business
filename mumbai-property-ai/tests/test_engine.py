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


def test_real_mode_and_fallback_never_strong_buy():
    assert c.post("/api/real/load").json()["markets"] == 5
    r = c.post("/api/ingest/text", json={"text": "2BHK 600 sq ft carpet Chembur 1.6 Cr ready to move", "source": "facebook"}).json()
    rep = c.post(f"/api/listings/{r['id']}/report", json={}).json()
    assert rep["price_check"]["confidence"] == "low" and rep["price_check"]["tier"] == "area-asking-benchmark"
    assert rep["rules_verdict"] == "VERIFY FIRST"


def test_igr_paste():
    txt = "2026-03-14  Flat 12, Sunrise CHS  Consideration 1,85,00,000  Area 55.7 sq.mt\n14/04/2026 Flat 4 value 2,10,00,000 area 640 sq ft"
    rows = c.post("/api/ingest/igr-text", json={"text": txt, "locality": "Chembur", "project_name": "Sunrise CHS"})
    assert rows.json()["imported"] == 2
    t = [x for x in store.all_("transactions") if x["project_name"] == "Sunrise CHS"]
    assert abs(t[0]["area_sqft"] - 599.5) < 1 and t[0]["agreement_value"] == 18_500_000


def test_rera_paste_rules():
    r = c.post("/api/ingest/rera-text", json={"text": "Project X  Registration P51900012345  Status: Lapsed"})
    assert r.json()["status"] == "lapsed"


def test_area_endpoint_and_research_without_key():
    c.post("/api/real/load")
    a = c.get("/api/area/Andheri").json()          # matches Andheri West/East
    assert a["reference_home"]["returns"]["scenarios"]["base"] and a["market"]["sources"]
    assert "error" in c.post("/api/area/Sion/research").json()   # no key: honest error, no fake data
    assert c.get("/api/area/Nowhere").status_code == 404
