from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Source = Literal["magicbricks", "99acres", "housing", "nobroker", "facebook", "instagram",
                 "whatsapp", "broker", "builder", "manual", "other"]
ConstructionStatus = Literal["ready", "under_construction", "unknown"]


class Listing(BaseModel):
    id: str = ""
    source: Source = "manual"
    url: str = ""
    title: str = ""
    locality: str = ""
    project_name: str = ""
    builder: str = ""
    rera_no: str = ""
    bhk: Optional[float] = None
    carpet_sqft: Optional[float] = None
    saleable_sqft: Optional[float] = None
    ask_price: float = 0                      # INR, as quoted
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    age_years: Optional[float] = None
    status: ConstructionStatus = "unknown"
    oc_received: Optional[bool] = None
    possession_date: str = ""                 # YYYY-MM for under-construction
    furnishing: Literal["unfurnished", "semi", "furnished", "unknown"] = "unknown"
    parking: Optional[int] = None
    expected_rent: Optional[float] = None     # INR / month, if the lister states one
    posted_date: str = ""
    contact: str = ""
    raw_text: str = ""
    extraction: str = ""                      # "llm" | "rules" | "import"


class Transaction(BaseModel):
    """One registered sale (Index-II record from IGR Maharashtra)."""
    id: str = ""
    date: str                                  # YYYY-MM-DD registration date
    locality: str
    project_name: str = ""
    rera_no: str = ""
    area_sqft: float
    area_basis: Literal["carpet", "builtup", "saleable"] = "carpet"
    agreement_value: float                     # INR, the consideration registered
    ready_reckoner_psf: Optional[float] = None
    doc_no: str = ""
    kind: Literal["resale", "primary"] = "resale"


class ReraProject(BaseModel):
    rera_no: str
    name: str
    builder: str = ""
    locality: str = ""
    status: Literal["ongoing", "completed", "lapsed", "revoked", "unknown"] = "unknown"
    registered_on: str = ""
    original_completion: str = ""              # YYYY-MM
    revised_completion: str = ""               # YYYY-MM
    total_units: Optional[int] = None
    sold_units: Optional[int] = None
    unsold_by_bhk: dict[str, int] = Field(default_factory=dict)
    complaints: int = 0
    litigation: bool = False
    last_updated: str = ""


class MarketParams(BaseModel):
    """Per-micro-market assumptions. These are *inputs you own*, not scraped facts."""
    locality: str
    ready_reckoner_psf: Optional[float] = None       # INR / sqft (RR, builtup basis)
    rent_psf_month: float                             # INR / carpet sqft / month, typical
    appreciation_bear: float = 0.02
    appreciation_base: float = 0.05
    appreciation_bull: float = 0.08
    rent_growth: float = 0.04
    note: str = ""


class BuyerInputs(BaseModel):
    down_payment_pct: float = 0.20
    loan_rate: float = 0.085
    loan_years: int = 20
    hold_years: int = 10
    is_woman_buyer: bool = False
    alt_return: float = 0.07                          # fixed-deposit style benchmark
    custom_rent: Optional[float] = None
    negotiated_price: Optional[float] = None
