from agents import Agent, WebSearchTool
from dotenv import load_dotenv

from helper import (
    get_macd,
    get_stock_price,
    get_technical_indicators,
)
from prompts import (
    FUNDAMENTAL_PROMPT,
    NEWS_MACRO_PROMPT,
    TECHNICAL_PROMPT,
    PORTFOLIO_MANAGER_PROMPT,
)
from schemas import (
    FundamentalResearchReport,
    NewsMacroResearchReport,
    TechnicalRiskReport,
    PortfolioReview,
)

load_dotenv()


fundamental_agent = Agent(
    name="Fundamental Researcher",
    model="gpt-5.6-sol",
    instructions=FUNDAMENTAL_PROMPT,
    tools=[WebSearchTool()],
    output_type=FundamentalResearchReport,
)


technical_agent = Agent(
    name="Technical and Risk Researcher",
    model="gpt-5.6-terra",
    instructions=TECHNICAL_PROMPT,
    tools=[
        get_stock_price,
        get_technical_indicators,
        get_macd,
    ],
    output_type=TechnicalRiskReport,
)


news_macro_agent = Agent(
    name="News and Macro Researcher",
    model="gpt-5.6-terra",
    instructions=NEWS_MACRO_PROMPT,
    tools=[WebSearchTool()],
    output_type=NewsMacroResearchReport,
)


portfolio_manager = Agent(
    name="Portfolio Manager",
    model="gpt-5.6-sol",
    instructions=PORTFOLIO_MANAGER_PROMPT,
    output_type=PortfolioReview,
)