from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import ai, demo, research, store
from .connectors import importers, text_ingest
from .models import BuyerInputs, Listing, MarketParams

app = FastAPI(title="Mumbai Property Research AI")
STATIC = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


@app.get("/api/status")
def status():
    return {"ai": {"enabled": ai.enabled(), "models": ai.MODELS},
            "counts": {c: len(store.all_(c)) for c in store.COLLECTIONS}}


@app.post("/api/demo/seed")
def seed():
    return demo.seed()


@app.get("/api/listings")
def listings(locality: str = "", min_price: float = 0, max_price: float = 0, bhk: Optional[float] = None):
    return research.rank({"locality": locality, "min_price": min_price, "max_price": max_price, "bhk": bhk})


class ReportReq(BuyerInputs):
    pass


@app.post("/api/listings/{lid}/report")
def report(lid: str, buyer: ReportReq = ReportReq()):
    r = research.build_report(lid, buyer)
    if not r:
        raise HTTPException(404, "listing not found")
    return r


class TextReq(BaseModel):
    text: str
    source: str = "manual"
    url: str = ""


@app.post("/api/ingest/text")
def ingest_text(req: TextReq):
    l = text_ingest.to_listing(req.text, req.source, req.url)
    if not l.ask_price:
        raise HTTPException(422, "Could not find a price in the text")
    l.id = store.put("listings", l.model_dump())
    return l


@app.post("/api/import/{kind}")
async def import_file(kind: str, file: UploadFile = File(...), source: str = Form("other")):
    content = await file.read()
    try:
        if kind == "listings":
            items = [(None, x.model_dump()) for x in importers.listings_from(content, file.filename, source)]
            n = store.put_many("listings", items)
        elif kind == "transactions":
            n = store.put_many("transactions", [(None, x.model_dump()) for x in importers.transactions_from(content, file.filename)])
        elif kind == "rera":
            n = store.put_many("rera", [(x.rera_no, x.model_dump()) for x in importers.rera_from(content, file.filename)])
        else:
            raise HTTPException(404, "kind must be listings|transactions|rera")
    except (ValueError, KeyError) as e:
        raise HTTPException(422, f"Could not parse file: {e}")
    return {"imported": n}


@app.put("/api/market")
def put_market(m: MarketParams):
    store.put("market", m.model_dump(), m.locality)
    return m
