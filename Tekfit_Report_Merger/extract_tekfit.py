import re
import os
from pathlib import Path
import pandas as pd
import pdfplumber

# ------- 可修改參數 -------
PDF_DIR = Path(__file__).parent / "data" #放 PDF 的資料夾
OUTPUT = Path(__file__).parent / "tekfit_merged.xlsx" # 輸出檔案位置&名稱
FREE_TYPES = ["50", "70", "90", "110", "free"] # 自由條件類別
# -------------------------

def parse_page1(text: str):
    date_raw = re.search(r"Date:\s*([0-9\-]+)", text).group(1)  # e.g., 03-06-2025-16-18-55
    date_parts = date_raw.split("-")[:3]
    date_fmt = f"{date_parts[2]}-{date_parts[0]}-{date_parts[1]}"  # YYYY-MM-DD
    return date_fmt

def parse_page3(text: str):
    stable = re.search(r"Stable\s+([0-9.]+)%\s+([0-9.]+)%", text)
    std = re.search(r"Average\s+Std\s+Angle\s+([0-9.]+)\s+degree\s+([0-9.]+)\s+degree", text)
    if not stable or not std:
        raise ValueError("無法解析穩定度或角度")
    stable_R, stable_L = map(float, stable.groups())
    std_R, std_L = map(float, std.groups())
    return stable_R, stable_L, std_R, std_L

def extract_info_from_filename(filename):
    base = Path(filename).stem
    match = re.match(r"(.*)-(\d+)", base)
    if not match:
        raise ValueError(f"檔名無法解析：{filename}")
    free_type, user_id = match.groups()
    return user_id, free_type

# 主收集 dict：key 為 user_id
data_by_user = {}

for pdf_path in PDF_DIR.rglob("*.pdf"):
    with pdfplumber.open(pdf_path) as pdf:
        if len(pdf.pages) < 3:
            print(f"[略過] {pdf_path.name} 頁數不足")
            continue
        try:
            user_id, free_type = extract_info_from_filename(pdf_path.name)
            if free_type not in FREE_TYPES:
                print(f"[略過] 未知條件類別 {free_type}")
                continue

            text1 = pdf.pages[0].extract_text()
            text3 = pdf.pages[2].extract_text()

            date_fmt = parse_page1(text1)
            sR, sL, stdR, stdL = parse_page3(text3)

        except Exception as e:
            print(f"[失敗] {pdf_path.name}: {e}")
            continue

    if user_id not in data_by_user:
        data_by_user[user_id] = {"ID": user_id, "Date": date_fmt}

    # 填入自由條件下的數值
    data_by_user[user_id][f"右腳穩定度_{free_type}"] = sR
    data_by_user[user_id][f"左腳穩定度_{free_type}"] = sL
    data_by_user[user_id][f"右腳偏移量_{free_type}"] = stdR
    data_by_user[user_id][f"左腳偏移量_{free_type}"] = stdL

# 欄位順序
columns = ["ID", "Date"]
for ft in FREE_TYPES:
    columns += [
        f"右腳穩定度_{ft}", f"左腳穩定度_{ft}",
        f"右腳偏移量_{ft}", f"左腳偏移量_{ft}"
    ]

# 轉成 DataFrame 並輸出
df = pd.DataFrame(data_by_user.values())
df = df.reindex(columns=columns)  # 自動補缺欄
df.to_excel(OUTPUT, index=False)
print(f"[完成] 匯出：{OUTPUT}")