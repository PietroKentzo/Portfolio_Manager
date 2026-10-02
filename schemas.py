from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# =========================
# 1. PORTFOLIO INPUT
# =========================

class PortfolioHolding(BaseModel):
    ticker: str
    market_value: float = Field(ge=0)
    cost_basis: float | None = Field(default=None, ge=0)
    shares: float | None = Field(default=None, ge=0)

    # Calculated from market_value; not required in porto.json.
    weight_pct: float | None = Field(default=None, ge=0, le=100)

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        ticker = value.strip().upper()
        if not ticker:
            raise ValueError("Ticker cannot be empty")
        return ticker


class PortfolioInput(BaseModel):
    date: str
    currency: str
    total_portfolio_value: float = Field(gt=0)
    cash: float = Field(ge=0)
    holdings: list[PortfolioHolding] = Field(min_length=1)

    # Calculated from cash; not required in porto.json.
    cash_pct: float | None = Field(default=None, ge=0, le=100)

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError("Date must use YYYY-MM-DD")
        return value

    @model_validator(mode="after")
    def validate_and_calculate_weights(self):
        tickers = [holding.ticker for holding in self.holdings]

        if len(tickers) != len(set(tickers)):
            raise ValueError("Portfolio contains duplicate tickers")

        calculated_total = self.cash + sum(
            holding.market_value for holding in self.holdings
        )

        if abs(calculated_total - self.total_portfolio_value) > 0.01:
            raise ValueError(
                f"Portfolio values total {calculated_total:.2f}, "
                f"but total_portfolio_value is "
                f"{self.total_portfolio_value:.2f}"
            )

        self.cash_pct = (
            100 * self.cash / self.total_portfolio_value
        )

        for holding in self.holdings:
            holding.weight_pct = (
                100 * holding.market_value
                / self.total_portfolio_value
            )

        return self

# =========================
# 2. PREVIOUS THESIS / STATE
# =========================

class PreviousHoldingState(BaseModel):
    ticker: str

    previous_action: Literal[
        "BUY",
        "HOLD",
        "REDUCE",
        "SELL"
    ] | None = None

    previous_conviction: float | None = Field(
        default=None,
        ge=0,
        le=1
    )

    previous_thesis: str | None = None

    thesis_invalidators: list[str] = []


class PortfolioHistoryState(BaseModel):
    date: str
    holdings: list[PreviousHoldingState]


# =========================
# 3. FUNDAMENTAL RESEARCH
# =========================

class FundamentalFinding(BaseModel):
    ticker: str

    outlook: Literal[
        "POSITIVE",
        "NEUTRAL",
        "NEGATIVE"
    ]

    summary: str

    positives: list[str]
    negatives: list[str]

    valuation_view: str
    earnings_view: str

    material_change: bool

    thesis_impact: Literal[
        "STRENGTHENED",
        "UNCHANGED",
        "WEAKENED"
    ]


class FundamentalResearchReport(BaseModel):
    findings: list[FundamentalFinding]


# =========================
# 4. NEWS / MACRO RESEARCH
# =========================

class NewsMacroFinding(BaseModel):
    ticker: str

    summary: str

    company_news: list[str]
    sector_news: list[str]
    macro_factors: list[str]
    catalysts: list[str]
    risks: list[str]

    material_change: bool

    impact: Literal[
        "POSITIVE",
        "NEUTRAL",
        "NEGATIVE"
    ]


class NewsMacroResearchReport(BaseModel):
    findings: list[NewsMacroFinding]


# =========================
# 5. TECHNICAL / RISK RESEARCH
# =========================

class TechnicalRiskFinding(BaseModel):
    ticker: str

    trend: Literal[
        "BULLISH",
        "NEUTRAL",
        "BEARISH"
    ]

    momentum: Literal[
        "STRONG",
        "MODERATE",
        "WEAK"
    ]

    summary: str

    support_levels: list[float] = []
    resistance_levels: list[float] = []

    volatility_risk: Literal[
        "LOW",
        "MEDIUM",
        "HIGH"
    ]

    technical_risks: list[str]

    material_change: bool


class TechnicalRiskReport(BaseModel):
    findings: list[TechnicalRiskFinding]


# =========================
# 6. SCENARIOS
# =========================

class Scenario(BaseModel):
    thesis: str

    probability: float = Field(
        ge=0,
        le=1
    )

    target_price: float | None = None


# =========================
# 7. FINAL HOLDING DECISION
# =========================

class HoldingDecision(BaseModel):
    ticker: str

    action: Literal[
        "BUY",
        "HOLD",
        "REDUCE",
        "SELL"
    ]

    conviction: float = Field(
        ge=0,
        le=1
    )

    thesis: str

    thesis_change: Literal[
        "STRENGTHENED",
        "UNCHANGED",
        "WEAKENED",
        "INVALIDATED"
    ]

    what_changed_today: list[str]

    bull_case: Scenario
    base_case: Scenario
    bear_case: Scenario

    thesis_invalidators: list[str]

    key_risks: list[str]


# =========================
# 8. FINAL PORTFOLIO REVIEW
# =========================

class PortfolioReview(BaseModel):
    date: str

    overall_risk: Literal[
        "LOW",
        "MEDIUM",
        "HIGH"
    ]

    market_regime: Literal[
        "RISK_ON",
        "NEUTRAL",
        "RISK_OFF"
    ]

    portfolio_summary: str

    suggested_cash_action: Literal[
        "DEPLOY",
        "HOLD_CASH",
        "RAISE_CASH"
    ]

    holdings: list[HoldingDecision]