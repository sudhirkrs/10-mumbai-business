# India businesses for sale: cross-source scan (9 Nov 2026)

All figures are seller or broker claims and unverified. Multiples are rough: ask divided by revenue, or by EBITDA/cash flow where the listing gives it.

## Sources read
| Source | Listings read | Notes |
|---|---|---|
| MergerDomo | 151 (all 17 pages) | Mid-market (₹5 Cr to ₹1,000 Cr). Full list in `mergerdomo-151-listings.csv`. |
| SMERGERS | newest 20 (see `smergers-latest-20.md`) | 4,645 listings in total, mostly small (under ₹5 Cr). |
| businessdeals.in | 17 on the homepage | Site shows 5,646 active listings, but the pagination endpoint was not used. |
| Synergy Business Brokers | 9 India listings | Net cash flow disclosed, $250K+ deals. |
| Not accessed | BusinessesForSale, BizBuySell, DealStream, BizQuest (all returned 403 to scripted requests, left alone); IndiBizBuy did not resolve; IndiaBizForSale and MergersCorp serve no usable listing data in plain HTML | |

## Top picks (best price vs. size and claimed profit)
| # | Business | Where | Revenue | Ask | Why it stands out | Source |
|---|---|---|---|---|---|---|
| 1 | CNC machine manufacturer | South India | ₹33.6 Cr | ₹12–15 Cr | Asks ~0.4x revenue; 2 live EOIs | MergerDomo |
| 2 | Luggage and travel-bag manufacturer ("profitable") | India | ₹12.2 Cr | ₹5.25–5.5 Cr | ~0.45x revenue; private-label customers; 2 EOIs | MergerDomo |
| 3 | Plastic-waste recycling machinery maker | India | ₹7.3 Cr | ₹19.5–20.5 Cr | Claims 45% EBITDA, so ~6x EBITDA; 10 EOIs means it will be contested | MergerDomo |
| 4 | IT managed-services (cloud partnerships) | Bengaluru | $2.31M | $1.46M | $362K cash flow, ~4x; recurring revenue | Synergy |
| 5 | IT services and managed solutions | Western India | ₹20.7 Cr | ₹20–25 Cr | ~1.1x revenue; Mumbai-friendly region | MergerDomo |
| 6 | Industrial automation and electrical solutions | India | ₹49.3 Cr | ₹40–50 Cr | ~0.9x revenue; 6 EOIs | MergerDomo |
| 7 | Institutional and corporate catering | Western India | ₹12.65 Cr | ₹8–10 Cr | ~0.7x revenue; contract-based | MergerDomo |
| 8 | Profitable e-commerce (50+ products) | India | ₹11 Cr | ₹4–6 Cr | ~0.45x revenue; check marketplace dependence | MergerDomo |
| 9 | Heavy fabrication and machining | India | ₹81.2 Cr | ₹80–90 Cr | ~1x revenue; established client base | MergerDomo |
| 10 | Flexible packaging and woven sacs | India | $3.6M | $2.5M | $400K cash flow, ~6x | Synergy |
| 11 | ISO-certified packaging company | North India | ₹14.1 Cr | ₹15–18 Cr | ~1.1x revenue | MergerDomo |
| 12 | Precision CNC for CV/auto parts | Dewas | $180K | $263K | 40% EBITDA claimed, ~3.6x; smallest ticket | SMERGERS |

## Watch-outs seen in this batch
- Hospitals asking 2–4x revenue (e.g. tertiary hospital ₹20.4 Cr revenue vs ₹80–100 Cr ask) are priced on assets and licences.
- Listings with 8–14 live EOIs (pharma packaging, 3PL, data science and AI consulting, pharma brand) will be bid up.
- Several MergerDomo listings are land, buildings or hotel sites, not operating businesses.
- Revenue is not shown on most MergerDomo listings, so the multiples above only cover those that disclose it.

## Mumbai/Western India angle
Western India listings on MergerDomo include IT services (₹20 Cr revenue), catering, logistics and customs brokerage (₹50–60 Cr ask), a 50-bed hospital (₹37 Cr revenue), environmental EPC, precision fasteners and a travel management firm (₹4.5–7 Cr ask). See the CSV and filter on "Western India".
