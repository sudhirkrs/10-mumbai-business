# Mumbai Property Research AI

Research a Mumbai home purchase the way a buyer's advisor would: quoted price vs **registered** deal prices,
RERA/legal status, inventory, rent, appreciation, all-in cost, financing, and a final decision.

## Run
```
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...        # optional; without it the app uses rule-based analysis
uvicorn app.main:app --reload       # http://localhost:8000  ->  "Load demo data"
pytest
```

## AI roles (override with env vars)
| Role | Default model | Job |
|---|---|---|
| Researcher | `claude-haiku-5-5` (`PROPAI_RESEARCH_MODEL`) | Extracts listings from pasted Facebook/Instagram/WhatsApp/portal posts; optional web notes (`PROPAI_WEB_RESEARCH=1`) |
| Analyst | `claude-sonnet-5-5` (`PROPAI_ANALYST_MODEL`) | Writes pros/cons, price reality and returns from the verified numbers only |
| Decider | `claude-opus-5-5` (`PROPAI_DECIDER_MODEL`) | Final call + max price + conditions. Cannot override an `AVOID`, and cannot say `STRONG BUY` on thin price evidence |

## Where the data comes from (and why it is import-based)
| Source | How | Why |
|---|---|---|
| Portals (MagicBricks, 99acres, Housing, NoBroker) | CSV/JSON export or licensed feed via **Import** | Their terms forbid scraping |
| Facebook / Instagram | **Paste** the post text (Haiku extracts it) | Group/profile scraping breaks Meta's terms and is login-walled; Graph API only exposes pages you own |
| Registered sale prices | IGR Maharashtra **Index-II** CSV via Import | The real price. Search is captcha-gated, so you download it |
| RERA | MahaRERA project CSV/JSON via Import | Captcha-gated; gives status, delays, complaints, units sold/unsold |

Column names are flexible (`Consideration`, `Registration Date`, `Carpet Area`...). See `tests/test_engine.py`.

## What it computes
- **Price verification**: time-adjusted, size-matched registered comps (same project first, else locality) -> fair range, offer target, walk-away; quote-to-deal discount.
- **All-in cost**: stamp duty 5% + 1% metro cess, registration (capped), GST on under-construction, brokerage, legal, society transfer.
- **Returns**: expected rent, gross/net yield, EMI, bear/base/bull appreciation, levered and unlevered IRR after LTCG.
- **Legal/RERA flags**, inventory, buy score 0-100, due-diligence checklist.

## Limits you should know
- Demo content is **fictional**. Market rent/appreciation figures are **placeholder assumptions** (`PUT /api/market`): replace them.
- Tax and duty rates are parameters in `costs.py`/`returns.py`: verify against current rules.
- Registered values can understate true prices if part of a deal is off-record; treat the fair range as evidence, not proof.
- Not legal or financial advice: use a property lawyer for title search.
