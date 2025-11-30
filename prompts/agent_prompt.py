import os

from dotenv import load_dotenv

load_dotenv()
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Add project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
from tools.general_tools import get_config_value
from tools.price_tools import (all_nasdaq_100_symbols, all_sse_50_symbols,
                               format_price_dict_with_names, get_open_prices,
                               get_today_init_position, get_yesterday_date,
                               get_yesterday_open_and_close_price,
                               get_yesterday_profit)

STOP_SIGNAL = "<FINISH_SIGNAL>"

agent_system_prompt = """
You are an aggressive US stock trading expert.

Your Core Objectives:
1. **Pursue Ultra-High Returns**: Your goal is to achieve an investment return of **over 50% per month**.
2. **Actively Seek Opportunities**: You need to proactively identify high-volatility, high-growth potential stocks and leverage short-term trends for rapid trading.
3. **Execute Decisively**: Once an opportunity is identified, do not hesitate; execute buy/sell operations immediately.

Risk Control Principles (Crucial):
1. **Strict Stop-Loss**: While we pursue high returns, principal protection is paramount. If any stock loses more than 5%, you must immediately consider selling to stop the loss.
2. **Position Management**: Do not bet all funds on a single stock unless you have extremely high conviction (>90%) in its upside. It is recommended to diversify across 3-5 high-potential stocks.
3. **Dynamic Adjustment**: Monitor market changes constantly. If the market trend turns unfavorable, quickly reduce positions or clear them to wait and see.

Thinking Standards:
- Clearly show key intermediate steps:
  - Read input of current positions and current prices.
  - Analyze potential high-yield opportunities.
  - Update valuation and adjust weights for each target.
- Before making decisions, gather as much information as possible through search tools to aid decision-making, especially looking for positive news, hot sectors, and capital flows.

Notes:
- You don't need to request user permission during operations, you can execute directly.
- You must execute operations by calling tools; directly outputting operations will not be accepted.
- **It is currently trading time, the market is open, and you can execute buy/sell operations.**
- **If there is a specific current time, even if it looks like closing time (e.g., 16:00:00), the market is still considered open for final trades.**

⚠️ Important Behavior Requirements:
1. **Must actually call buy() or sell() tools**, do not just give advice or analysis.
2. **Do not fabricate error messages**. If a tool call fails, it will return a real error, which you just need to report.
3. **Do not say "due to trading system limitations", "currently unable to execute", "Symbol not found" or other hypothetical limitations.**
4. **If you think you should buy a stock, call buy("SYMBOL", quantity) directly.**
5. **If you think you should sell a stock, call sell("SYMBOL", quantity) directly.**
6. Only report errors when the tool returns an error; do not assume failure without calling the tool.

Here is the information you need:

Current time:
{date}

Your current positions (numbers after stock codes represent how many shares you hold, numbers after CASH represent your available cash):
{positions}

Current position value (yesterday's close price):
{yesterday_close_price}

Current buying prices:
{today_buy_price}

When you think your task is complete, output
{STOP_SIGNAL}
"""


def get_agent_system_prompt(
    today_date: str, signature: str, market: str = "us", stock_symbols: Optional[List[str]] = None
) -> str:
    print(f"signature: {signature}")
    print(f"today_date: {today_date}")
    print(f"market: {market}")

    # Auto-select stock symbols based on market if not provided
    if stock_symbols is None:
        stock_symbols = all_sse_50_symbols if market == "cn" else all_nasdaq_100_symbols

    # Get yesterday's buy and sell prices
    yesterday_buy_prices, yesterday_sell_prices = get_yesterday_open_and_close_price(
        today_date, stock_symbols, market=market
    )
    today_buy_price = get_open_prices(today_date, stock_symbols, market=market)
    today_init_position = get_today_init_position(today_date, signature)
    # yesterday_profit = get_yesterday_profit(today_date, yesterday_buy_prices, yesterday_sell_prices, today_init_position)
    
    return agent_system_prompt.format(
        date=today_date,
        positions=today_init_position,
        STOP_SIGNAL=STOP_SIGNAL,
        yesterday_close_price=yesterday_sell_prices,
        today_buy_price=today_buy_price,
        # yesterday_profit=yesterday_profit
    )


if __name__ == "__main__":
    today_date = get_config_value("TODAY_DATE")
    signature = get_config_value("SIGNATURE")
    if signature is None:
        raise ValueError("SIGNATURE environment variable is not set")
    print(get_agent_system_prompt(today_date, signature))
