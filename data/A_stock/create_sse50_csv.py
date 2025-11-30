import os
import csv

sse_50_codes = [
    "600519.SHH", "601318.SHH", "600036.SHH", "601899.SHH", "600900.SHH",
    "601166.SHH", "600276.SHH", "600030.SHH", "603259.SHH", "688981.SHH",
    "688256.SHH", "601398.SHH", "688041.SHH", "601211.SHH", "601288.SHH",
    "601328.SHH", "688008.SHH", "600887.SHH", "600150.SHH", "601816.SHH",
    "601127.SHH", "600031.SHH", "688012.SHH", "603501.SHH", "601088.SHH",
    "600309.SHH", "601601.SHH", "601668.SHH", "603993.SHH", "601012.SHH",
    "601728.SHH", "600690.SHH", "600809.SHH", "600941.SHH", "600406.SHH",
    "601857.SHH", "601766.SHH", "601919.SHH", "600050.SHH", "600760.SHH",
    "601225.SHH", "600028.SHH", "601988.SHH", "688111.SHH", "601985.SHH",
    "601888.SHH", "601628.SHH", "601600.SHH", "601658.SHH", "600048.SHH"
]

# Known names mapping (partial)
known_names = {
    "600519.SH": "贵州茅台",
    "601318.SH": "中国平安",
    "600036.SH": "招商银行",
    "601899.SH": "紫金矿业",
    "600900.SH": "长江电力",
    "601166.SH": "兴业银行",
    "600276.SH": "恒瑞医药",
    "600030.SH": "中信证券",
    "603259.SH": "药明康德",
    "688981.SH": "中芯国际",
    "601398.SH": "工商银行",
    "601288.SH": "农业银行",
    "601988.SH": "中国银行",
    "601939.SH": "建设银行",
    "601857.SH": "中国石油",
    "600028.SH": "中国石化",
    "601088.SH": "中国神华",
    "601628.SH": "中国人寿",
    "601328.SH": "交通银行",
    "600887.SH": "伊利股份",
    "601919.SH": "中远海控",
    "600050.SH": "中国联通",
    "601728.SH": "中国电信",
    "600941.SH": "中国移动",
}

output_dir = "./data/A_stock/A_stock_data"
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, "sse_50_weight.csv")

with open(output_file, "w", encoding="utf-8", newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["con_code", "stock_name"])
    
    for code in sse_50_codes:
        # Convert .SHH to .SH
        sh_code = code.replace(".SHH", ".SH")
        name = known_names.get(sh_code, sh_code) # Use code as name if unknown
        writer.writerow([sh_code, name])

print(f"Created {output_file} with {len(sse_50_codes)} entries.")
