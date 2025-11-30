import os
import requests
from dotenv import load_dotenv
import json
import time

load_dotenv()

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

def get_daily_price(SYMBOL: str):
    FUNCTION = "TIME_SERIES_INTRADAY"
    INTERVAL = "60min"
    OUTPUTSIZE = 'full'
    APIKEY = os.getenv("ALPHAADVANTAGE_API_KEY")
    url = f'https://www.alphavantage.co/query?function={FUNCTION}&symbol={SYMBOL}&interval={INTERVAL}&outputsize={OUTPUTSIZE}&entitlement=delayed&extended_hours=false&apikey={APIKEY}'
    
    try:
        r = requests.get(url)
        data = r.json()
        # print(data) # Reduce noise
    except Exception as e:
        print(f"Error fetching data for {SYMBOL}: {e}")
        return

    if data.get("Note") is not None or data.get("Information") is not None:
        print(f"Error or Rate Limit for {SYMBOL}: {data}")
        return
        
    if "Time Series (60min)" not in data:
        print(f"No Time Series data for {SYMBOL}")
        return

    print(f"Successfully fetched data for {SYMBOL}")
    update_json(data, SYMBOL)

if __name__ == "__main__":
    for symbol in all_nasdaq_100_symbols:
        get_daily_price(symbol)
        # Alpha Vantage free tier limit is 5 calls per minute, so we wait
        print("Waiting 12s to respect API rate limits...")
        time.sleep(12)

    get_daily_price("QQQ")
