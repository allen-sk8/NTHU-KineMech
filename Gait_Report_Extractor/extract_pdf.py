import os
import re
import pdfplumber
import pandas as pd
from pathlib import Path

# 輸入資料夾與輸出路徑
pdf_folder = Path(__file__).parent / "data"
output_file = Path(__file__).parent / "summary.xlsx"

pdf_files = list(pdf_folder.glob("*.pdf"))
records = []

for pdf_path in pdf_files:
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages)

    record = {"filename": pdf_path.name}


    # ===== Basic Info（允許沒空格）=====
    match = re.search(r"Name:\s*(.*?)\s*Date:\s*(.*?)\s*Time:\s*(.*?)\s*Cadence:\s*([\d\.]+)", text)
    if match:
        record["Name"] = match.group(1)
        record["Date"] = match.group(2)
        record["Time"] = match.group(3)
        record["Cadence"] = match.group(4)
    else:
        # optional: print warning for missing values
        print(f"[!] Missing basic info in {pdf_path.name}")


    match = re.search(r"Height:\s*(\d+cm)\s+Weight:\s*(\d+kg)\s+Gender:\s*(.*?)\s+Age:\s*(\d+yr)", text)
    if match:
        record["Height"] = match.group(1)
        record["Weight"] = match.group(2)
        record["Gender"] = match.group(3) if match.group(3).strip() else "N/A"
        record["Age"] = match.group(4)

    # ===== Motion Type Result =====
    '''match = re.search(r"Motion Type\s+(.*?)\s+(.*?)\n", text)
    if match:
        record["MotionType_Left"] = match.group(1)
        record["MotionType_Right"] = match.group(2)'''

    for item in ["Supination", "Pronation", "OverPronation"]:
        match = re.search(rf"{item}\s+([\d\.]+%)\s+([\d\.]+%)", text)
        if match:
            record[f"{item}_Left"] = match.group(1)
            record[f"{item}_Right"] = match.group(2)

    match = re.search(r"(Your .*?walking pattern\.)", text)
    if match:
        record["Pattern_Description"] = match.group(1)

    # ===== Stability =====
    match = re.search(r"Stability\s+([\d\.]+%)\s+([\d\.]+%)", text)
    if match:
        record["Stability_Left"] = match.group(1)
        record["Stability_Right"] = match.group(2)

    match = re.search(r"Average Sway Angle\s+±\s*([\d\.]+) degree\s+±\s*([\d\.]+) degree", text)
    if match:
        record["SwayAngle_Left"] = match.group(1)
        record["SwayAngle_Right"] = match.group(2)

    # ===== Motion Result =====
    match = re.search(r"Stance Phase Time\s+([\d\.]+%)\s+([\d\.]+%)", text)
    if match:
        record["StancePhase_Left"] = match.group(1)
        record["StancePhase_Right"] = match.group(2)

    match = re.search(r"Swing Phase Time\s+([\d\.]+%)\s+([\d\.]+%)", text)
    if match:
        record["SwingPhase_Left"] = match.group(1)
        record["SwingPhase_Right"] = match.group(2)

    match = re.search(r"Stance Angle\s+([\d\.\-]+) degree\s+([\d\.\-]+) degree", text)
    if match:
        record["StanceAngle_Left"] = match.group(1)
        record["StanceAngle_Right"] = match.group(2)

    match = re.search(r"Angle Balance\s+([\d\.]+%)\s+([\d\.]+%)", text)
    if match:
        record["AngleBalance_Left"] = match.group(1)
        record["AngleBalance_Right"] = match.group(2)

    match = re.search(r"Power Balance\s+([\d\.]+%)\s+([\d\.]+%)", text)
    if match:
        record["PowerBalance_Left"] = match.group(1)
        record["PowerBalance_Right"] = match.group(2)

    records.append(record)

# ===== 輸出結果 =====
df = pd.DataFrame(records)
df.to_excel(output_file, index=False)
print(f"[✓] 共處理 {len(records)} 份 PDF，已輸出至 {output_file}")
