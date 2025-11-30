import os
import json
import time
import pandas as pd
from futu import OpenQuoteContext, KLType, AuType, KL_FIELD, RET_OK
from dotenv import load_dotenv

load_dotenv()

# List of NASDAQ 100 symbols
all_nasdaq_100_symbols = [
    "NVDA", "MSFT", "AAPL", "GOOG", "GOOGL", "AMZN", "META", "AVGO", "TSLA", "NFLX",
    "PLTR", "COST", "ASML", "AMD", "CSCO", "AZN", "TMUS", "MU", "LIN", "PEP",
    "SHOP", "APP", "INTU", "AMAT", "LRCX", "PDD", "QCOM", "ARM", "INTC", "BKNG",
    "AMGN", "TXN", "ISRG", "GILD", "KLAC", "PANW", "ADBE", "HON", "CRWD", "CEG",
    "ADI", "ADP", "DASH", "CMCSA", "VRTX", "MELI", "SBUX", "CDNS", "ORLY", "SNPS",
    "MSTR", "MDLZ", "ABNB", "MRVL", "CTAS", "TRI", "MAR", "MNST", "CSX", "ADSK",
    "PYPL", "FTNT", "AEP", "WDAY", "REGN", "ROP", "NXPI", "DDOG", "AXON", "ROST",
    "IDXX", "EA", "PCAR", "FAST", "EXC", "TTWO", "XEL", "ZS", "PAYX", "WBD",
    "BKR", "CPRT", "CCEP", "FANG", "TEAM", "CHTR", "KDP", "MCHP", "GEHC", "VRSK",
    "CTSH", "CSGP", "KHC", "ODFL", "DXCM", "TTD", "ON", "BIIB", "LULU", "CDW", "GFS"
]

def update_json(data: dict, SYMBOL: str):
    # Ensure directory exists
    output_dir = "./US_stock_data"
    os.makedirs(output_dir, exist_ok=True)
    
    file_path = os.path.join(output_dir, f'daily_prices_{SYMBOL}.json')
    
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
            
            # Merge "Time Series (60min)"
            old_ts = old_data.get("Time Series (60min)", {})
            new_ts = data.get("Time Series (60min)", {})
            merged_ts = {**old_ts, **new_ts}
            
            merged_data = data.copy()
            merged_data["Time Series (60min)"] = merged_ts
            
            if "Meta Data" not in merged_data and "Meta Data" in old_data:
                merged_data["Meta Data"] = old_data["Meta Data"]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(merged_data, f, ensure_ascii=False, indent=4)
        else:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        
        # QQQ special handling
        if SYMBOL == "QQQ":
            file_path_qqq = os.path.join(output_dir, f'Adaily_prices_{SYMBOL}.json')
            if os.path.exists(file_path_qqq):
                with open(file_path_qqq, 'r', encoding='utf-8') as f:
                    old_data = json.load(f)
                old_ts = old_data.get("Time Series (60min)", {})
                new_ts = data.get("Time Series (60min)", {})
                merged_ts = {**old_ts, **new_ts}
                merged_data = data.copy()
                merged_data["Time Series (60min)"] = merged_ts
                if "Meta Data" not in merged_data and "Meta Data" in old_data:
                    merged_data["Meta Data"] = old_data["Meta Data"]
                with open(file_path_qqq, 'w', encoding='utf-8') as f:
                    json.dump(merged_data, f, ensure_ascii=False, indent=4)
            else:
                with open(file_path_qqq, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                    
    except (IOError, json.JSONDecodeError, KeyError) as e:
        print(f"Error when update {SYMBOL}: {e}")
        raise

def fetch_futu_data(quote_ctx, symbol):
    """
    Fetch 60-minute K-line data from Futu OpenD and convert to Alpha Vantage format.
    """
    futu_symbol = f"US.{symbol}"
    
    # Request historical K-line data
    # KLType.K_60M for 60-minute data
    # AuType.QFQ for Forward Adjusted prices (usually preferred for analysis)
    ret, data, page_req_key = quote_ctx.request_history_kline(
        futu_symbol,
        start='2024-01-01', # Fetch data from start of 2024 to ensure coverage
        end=None, # To current
        ktype=KLType.K_60M,
        autype=AuType.QFQ,

        max_count=1000,
        page_req_key=None,
        extended_time=False
    )
    
    if ret == RET_OK:
        # Process data
        time_series = {}
        for index, row in data.iterrows():
            # Futu time format: "2023-10-27 16:00:00"
            timestamp = row['time_key']
            
            time_series[timestamp] = {
                "1. open": f"{row['open']:.4f}",
                "2. high": f"{row['high']:.4f}",
                "3. low": f"{row['low']:.4f}",
                "4. close": f"{row['close']:.4f}",
                "5. volume": str(int(row['volume']))
            }
            
        # Construct final JSON structure
        final_data = {
            "Meta Data": {
                "1. Information": "Intraday (60min) prices and volumes",
                "2. Symbol": symbol,
                "3. Last Refreshed": data.iloc[-1]['time_key'] if not data.empty else "",
                "4. Interval": "60min",
                "5. Output Size": "Full",
                "6. Time Zone": "US/Eastern" 
            },
            "Time Series (60min)": time_series
        }
        
        return final_data
    else:
        print(f"Futu API Error for {symbol}: {data}")
        return None

def main():
    # Initialize Futu OpenQuoteContext
    # Assuming OpenD is running on localhost:11111
    try:
        quote_ctx = OpenQuoteContext(host='127.0.0.1', port=11111)
        print("Connected to Futu OpenD")
    except Exception as e:
        print(f"Failed to connect to Futu OpenD: {e}")
        print("Please ensure Futu OpenD is running and listening on 127.0.0.1:11111")
        return

    try:
        # Process all symbols
        for symbol in all_nasdaq_100_symbols:
            print(f"Fetching data for {symbol}...")
            data = fetch_futu_data(quote_ctx, symbol)
            
            if data:
                update_json(data, symbol)
                print(f"Successfully updated {symbol}")
            
            # Small delay to avoid overwhelming the connection
            time.sleep(0.5)
            
        # Process QQQ
        print("Fetching data for QQQ...")
        data = fetch_futu_data(quote_ctx, "QQQ")
        if data:
            update_json(data, "QQQ")
            print("Successfully updated QQQ")
            
    finally:
        quote_ctx.close()
        print("Connection closed")

if __name__ == "__main__":
    main()
