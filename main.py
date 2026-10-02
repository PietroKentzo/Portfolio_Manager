import asyncio
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from agents import Runner

from porto_agent import (
    fundamental_agent,
    news_macro_agent,
    technical_agent,
    portfolio_manager,
)
from schemas import PortfolioInput, PortfolioReview


BASE_DIR = Path(__file__).resolve().parent

PORTFOLIO_PATH = Path(
    os.getenv(
        "PORTFOLIO_PATH",
        str(BASE_DIR / "data" / "porto.json"),
    )
)

HISTORY_PATH = BASE_DIR / "data" / "history.jsonl"


def load_portfolio() -> PortfolioInput:
    if not PORTFOLIO_PATH.is_file():
        raise FileNotFoundError(
            f"Portfolio file not found: {PORTFOLIO_PATH}. "
            "Create data/porto.json or set PORTFOLIO_PATH."
        )

    with PORTFOLIO_PATH.open(encoding="utf-8") as file:
        raw_portfolio = json.load(file)

    return PortfolioInput.model_validate(raw_portfolio)


def load_history(limit: int = 5) -> list[dict]:
    if limit < 0:
        raise ValueError("History limit cannot be negative")

    if limit == 0 or not HISTORY_PATH.exists():
        return []

    lines = [
        line
        for line in HISTORY_PATH.read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
    ]

    return [
        json.loads(line)
        for line in lines[-limit:]
    ]


def check_coverage(
    report_name: str,
    expected_tickers: set[str],
    returned_tickers: list[str],
) -> None:
    counts = Counter(
        ticker.upper()
        for ticker in returned_tickers
    )

    missing = sorted(expected_tickers - counts.keys())
    extra = sorted(counts.keys() - expected_tickers)
    duplicates = sorted(
        ticker
        for ticker, count in counts.items()
        if count > 1
    )

    if missing or extra or duplicates:
        raise ValueError(
            f"{report_name} ticker coverage failed. "
            f"Missing: {missing}; "
            f"extra: {extra}; "
            f"duplicates: {duplicates}"
        )


async def run_daily_portfolio_review(
    portfolio: PortfolioInput,
    history: list[dict],
) -> PortfolioReview:
    expected_tickers = {
        holding.ticker
        for holding in portfolio.holdings
    }

    context = {
        "portfolio": portfolio.model_dump(mode="json"),
        "recent_history": history,
    }

    research_input = json.dumps(context)

    fundamental_result, news_result, technical_result = (
        await asyncio.gather(
            Runner.run(fundamental_agent, research_input),
            Runner.run(news_macro_agent, research_input),
            Runner.run(technical_agent, research_input),
        )
    )

    fundamental_report = fundamental_result.final_output
    news_report = news_result.final_output
    technical_report = technical_result.final_output

    check_coverage(
        "Fundamental report",
        expected_tickers,
        [
            finding.ticker
            for finding in fundamental_report.findings
        ],
    )

    check_coverage(
        "News and macro report",
        expected_tickers,
        [
            finding.ticker
            for finding in news_report.findings
        ],
    )

    check_coverage(
        "Technical report",
        expected_tickers,
        [
            finding.ticker
            for finding in technical_report.findings
        ],
    )

    manager_input = {
        **context,
        "fundamental_report": fundamental_report.model_dump(
            mode="json"
        ),
        "news_macro_report": news_report.model_dump(
            mode="json"
        ),
        "technical_report": technical_report.model_dump(
            mode="json"
        ),
    }

    manager_result = await Runner.run(
        portfolio_manager,
        input=json.dumps(manager_input),
    )

    review: PortfolioReview = manager_result.final_output

    check_coverage(
        "Final portfolio review",
        expected_tickers,
        [
            decision.ticker
            for decision in review.holdings
        ],
    )

    if review.date != portfolio.date:
        raise ValueError(
            f"Review date {review.date} does not match "
            f"portfolio date {portfolio.date}"
        )

    return review


def append_history(review: PortfolioReview) -> None:
    HISTORY_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    record = review.model_dump(mode="json")
    record["recorded_at_utc"] = (
        datetime.now(timezone.utc).isoformat()
    )

    with HISTORY_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record) + "\n")


async def main() -> None:
    portfolio = load_portfolio()
    history = load_history(limit=5)

    review = await run_daily_portfolio_review(
        portfolio,
        history,
    )

    print(review.model_dump_json(indent=2))
    append_history(review)


if __name__ == "__main__":
    asyncio.run(main())