# extract_pdf_gui.py
import os
import re
import pdfplumber
import pandas as pd
from pathlib import Path
from tkinter import filedialog, Tk, messagebox

# ==== 彈出視窗讓使用者選擇資料夾 ====
root = Tk()
root.withdraw()  # 不顯示主視窗
folder_selected = filedialog.askdirectory(title="請選擇 PDF 資料夾")

if not folder_selected:
    messagebox.showinfo("提醒", "你沒有選資料夾，程式將結束")
    exit()

pdf_folder = Path(folder_selected)
output_file = pdf_folder.parent / "summary.xlsx"
pdf_files = list(pdf_folder.glob("*.pdf"))
records = []

for pdf_path in pdf_files:
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages)

    record = {"filename": pdf_path.name}

    # Basic Info（容錯強）
    match = re.search(r"Name:\s*(.*?)\s*Date:\s*(.*?)\s*Time:\s*(.*?)\s*Cadence:\s*([\d\.]+)", text)
    if match:
        record["Name"] = match.group(1)
        record["Date"] = match.group(2)
        record["Time"] = match.group(3)
        record["Cadence"] = match.group(4)

    match = re.search(r"Height:\s*(\d+cm)\s*Weight:\s*(\d+kg)\s*Gender:\s*(.*?)\s*Age:\s*(\d+yr)", text)
    if match:
        record["Height"] = match.group(1)
        record["Weight"] = match.group(2)
        record["Gender"] = match.group(3) if match.group(3).strip() else "N/A"
        record["Age"] = match.group(4)

    '''# Motion Type
    match = re.search(r"Motion Type\s+(.*?)\s+(.*?)\n", text)
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

    # Stability
    match = re.search(r"Stability\s+([\d\.]+%)\s+([\d\.]+%)", text)
    if match:
        record["Stability_Left"] = match.group(1)
        record["Stability_Right"] = match.group(2)

    match = re.search(r"Average Sway Angle\s+±\s*([\d\.]+) degree\s+±\s*([\d\.]+) degree", text)
    if match:
        record["SwayAngle_Left"] = match.group(1)
        record["SwayAngle_Right"] = match.group(2)

    # Motion Result
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

# 匯出結果
df = pd.DataFrame(records)
df.to_excel(output_file, index=False)

messagebox.showinfo("成功", f"共處理 {len(records)} 份 PDF，結果已輸出至：\n{output_file}")
