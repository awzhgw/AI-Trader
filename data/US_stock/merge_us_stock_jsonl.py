import glob
import json
import os

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

# Merge all daily_price*.json files from US_stock_data
current_dir = os.path.dirname(__file__)
data_dir = os.path.join(current_dir, "US_stock_data")
pattern = os.path.join(data_dir, "daily_prices_*.json")
files = sorted(glob.glob(pattern))

output_file = os.path.join(current_dir, "merged.jsonl")

processed_count = 0
skipped_count = 0

with open(output_file, "w", encoding="utf-8") as fout:
    for fp in files:
        basename = os.path.basename(fp)
        # Check if symbol is in NASDAQ 100 list
        # Extract symbol from filename: daily_prices_SYMBOL.json
        symbol_part = basename.replace("daily_prices_", "").replace(".json", "")
        
        if symbol_part not in all_nasdaq_100_symbols:
            skipped_count += 1
            continue
            
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Rename keys: "1. open" -> "1. buy price"; "4. close" -> "4. sell price"
        # For the latest date, keep only "1. buy price"
        try:
            # Find Time Series key
            series = None
            for key, value in data.items():
                if key.startswith("Time Series"):
                    series = value
                    break
            
            if isinstance(series, dict) and series:
                # Rename keys for all dates
                for d, bar in list(series.items()):
                    if not isinstance(bar, dict):
                        continue
                    if "1. open" in bar:
                        bar["1. buy price"] = bar.pop("1. open")
                    if "4. close" in bar:
                        bar["4. sell price"] = bar.pop("4. close")
                
                # Handle latest date: keep only buy price
                if series:
                    latest_date = max(series.keys())
                    latest_bar = series.get(latest_date, {})
                    if isinstance(latest_bar, dict):
                        buy_val = latest_bar.get("1. buy price")
                        series[latest_date] = {"1. buy price": buy_val} if buy_val is not None else {}
                
                # Update Meta Data description
                meta = data.get("Meta Data", {})
                if isinstance(meta, dict):
                    meta["1. Information"] = "Daily Prices (buy price, high, low, sell price) and Volumes"
            
            processed_count += 1
        except Exception as e:
            print(f"Error processing {basename}: {e}")
            pass

        fout.write(json.dumps(data, ensure_ascii=False) + "\n")

print(f"✅ Merge complete!")
print(f"📊 Statistics:")
print(f"   - Successfully processed: {processed_count} files")
print(f"   - Skipped: {skipped_count} files")
print(f"   - Output file: {output_file}")
