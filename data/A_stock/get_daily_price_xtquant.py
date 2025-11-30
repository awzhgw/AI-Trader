import os
import time
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from xtquant import xtdata

# Add project root to path to import tools
import sys
project_root = str(Path(__file__).resolve().parents[2])
sys.path.insert(0, project_root)
from tools.price_tools import all_sse_50_symbols

def get_sse50_codes() -> List[str]:
    """Get SSE 50 stock codes."""
    # Try to get from xtdata sector first
    try:
        sector_list = xtdata.get_sector_list()
        target_sector = None
        for sector in sector_list:
            if "上证50" in sector and "指数" not in sector: # Try to find the constituent sector
                target_sector = sector
                break
        
        if not target_sector:
             # Fallback to "上证50" directly
             target_sector = "上证50"
        
        stocks = xtdata.get_stock_list_in_sector(target_sector)
        if stocks:
            print(f"Found {len(stocks)} stocks in sector '{target_sector}'")
            return stocks
    except Exception as e:
        print(f"Error getting sector data: {e}")
    
    # Fallback to hardcoded list
    print("Using fallback SSE 50 list from tools.price_tools")
    return all_sse_50_symbols

def download_data(stock_list: List[str], start_time: str):
    """Download history data."""
    print(f"Downloading history data for {len(stock_list)} stocks from {start_time}...")
    xtdata.download_history_data2(stock_list, period='1d', start_time=start_time)
    print("Download complete.")

def get_daily_data(stock_list: List[str], start_time: str) -> pd.DataFrame:
    """Get daily data and convert to long format DataFrame."""
    print("Fetching local data...")
    # Fields to fetch
    fields = ['open', 'high', 'low', 'close', 'volume', 'amount']
    
    # get_local_data returns dict { field: DataFrame(index=stocks, columns=times) }
    data_dict = xtdata.get_local_data(
        field_list=fields,
        stock_list=stock_list,
        period='1d',
        start_time=start_time,
        count=-1,
        dividend_type='front', # Forward adjusted
        fill_data=True
    )
    
    # Convert to long format
    all_dfs = []
    for stock in stock_list:
        stock_data = {}
        valid_data = False
        
        # Extract time index from one of the fields (e.g., open)
        if 'open' in data_dict and not data_dict['open'].empty:
            # The columns are timestamps (int or str), index is stock code
            # Wait, docs say: "index为stock_list，columns为time_list"
            # So data_dict['open'].loc[stock] gives a Series with time as index
            
            times = data_dict['open'].columns.tolist()
            stock_data['trade_date'] = times
            stock_data['ts_code'] = stock
            
            for field in fields:
                if field in data_dict:
                    # Get values for this stock
                    values = data_dict[field].loc[stock].values
                    stock_data[field] = values
                    valid_data = True
            
            if valid_data:
                df_stock = pd.DataFrame(stock_data)
                all_dfs.append(df_stock)
    
    if not all_dfs:
        return pd.DataFrame()
        
    final_df = pd.concat(all_dfs, ignore_index=True)
    
    # Format trade_date
    # xtdata returns dates as 'YYYYMMDD' strings or integers usually
    final_df['trade_date'] = final_df['trade_date'].astype(str)
    
    return final_df

def main():
    start_date = "20251001"
    
    # 1. Get Stock List
    stock_list = get_sse50_codes()
    if not stock_list:
        print("No stocks found.")
        return

    # 2. Download Data
    download_data(stock_list, start_date)
    
    # 3. Get Data
    df = get_daily_data(stock_list, start_date)
    
    if df.empty:
        print("No data fetched.")
        return
        
    # 4. Save to CSV
    output_dir = Path(__file__).parent / "A_stock_data"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "daily_prices_sse_50_xt.csv"
    
    # Rename columns to match Tushare format for consistency if needed, 
    # but I'll stick to standard names and handle mapping in merge script.
    # XtQuant: open, high, low, close, volume, amount
    # Tushare: open, high, low, close, vol, amount
    # I'll rename volume -> vol to match Tushare's convention partially
    df = df.rename(columns={'volume': 'vol'})
    
    df.to_csv(output_file, index=False)
    print(f"Data saved to {output_file}")
    print(f"Shape: {df.shape}")

if __name__ == "__main__":
    main()
