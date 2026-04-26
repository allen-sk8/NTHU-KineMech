import os
import re
import pdfplumber
import pandas as pd
from pathlib import Path
from tkinter import filedialog, Tk, messagebox

# 彈出選擇資料夾
root = Tk()
root.withdraw()
folder_selected = filedialog.askdirectory(title="請選擇 PDF 資料夾")
if not folder_selected:
    messagebox.showinfo("提醒", "你沒有選資料夾，程式結束")
    exit()

pdf_folder = Path(folder_selected)
output_file = pdf_folder.parent / "步態分析彙整.xlsx"
pdf_files = list(pdf_folder.glob("*.pdf"))
records = []

for pdf_path in pdf_files:
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages)

    record = {"檔名": pdf_path.name}

    # ==== 基本資料 ====
    match = re.search(r"姓名[:：]\s*(\S+)\s*日期[:：]?\s*([\d\-: ]+)\s*訓練時間[:：]?\s*([\d\.]+)分?\s*步頻[:：]?\s*([\d\.]+)", text)
    if match:
        record["姓名"] = match.group(1)
        record["日期"] = match.group(2)
        record["訓練時間（分）"] = match.group(3)
        record["步頻"] = match.group(4)

    match = re.search(r"身高[:：]?\s*(\d+)公分\s*體重[:：]?\s*(\d+)公斤\s*性别[:：]?\s*(.*?)\s*年齡[:：]?\s*(\d+)歲", text)
    if match:
        record["身高"] = match.group(1)
        record["體重"] = match.group(2)
        record["性別"] = match.group(3).strip() if match.group(3).strip() else "N/A"
        record["年齡"] = match.group(4)

    # ==== 姿態判斷 ====
    for label in ["外旋百分比", "內旋百分比", "過度內旋百分比"]:
        match = re.search(rf"{label}\s*([\d\.]+%)\s*([\d\.]+%)", text)
        if match:
            record[f"{label}_左腳"] = match.group(1)
            record[f"{label}_右腳"] = match.group(2)

    match = re.search(r"(你的右腳步態為.*?)$", text, re.MULTILINE)
    if match:
        record["姿態描述"] = match.group(1)

    # ==== 穩定度 ====
    match = re.search(r"穩定度百分比\s*([\d\.]+%)\s*([\d\.]+%)", text)
    if match:
        record["穩定度_左腳"] = match.group(1)
        record["穩定度_右腳"] = match.group(2)

    match = re.search(r"平均晃動角度±\s*([\d\.]+)度±\s*([\d\.]+)度", text)
    if match:
        record["晃動角_左腳"] = match.group(1)
        record["晃動角_右腳"] = match.group(2)

    # ==== 動作分析 ====
    match = re.search(r"站立期百分比\s*([\d\.]+%)\s*([\d\.]+%)", text)
    if match:
        record["站立期_左腳"] = match.group(1)
        record["站立期_右腳"] = match.group(2)

    match = re.search(r"擺盪期百分比\s*([\d\.]+%)\s*([\d\.]+%)", text)
    if match:
        record["擺盪期_左腳"] = match.group(1)
        record["擺盪期_右腳"] = match.group(2)

    match = re.search(r"站立期晃動角度\s*([\d\.]+)度\s*([\d\.]+)度", text)
    if match:
        record["站晃角_左腳"] = match.group(1)
        record["站晃角_右腳"] = match.group(2)

    match = re.search(r"左右腳晃動比\s*([\d\.]+%)\s*([\d\.]+%)", text)
    if match:
        record["晃動比_左腳"] = match.group(1)
        record["晃動比_右腳"] = match.group(2)

    match = re.search(r"左右腳承重比\s*([\d\.]+%)\s*([\d\.]+%)", text)
    if match:
        record["承重比_左腳"] = match.group(1)
        record["承重比_右腳"] = match.group(2)

    records.append(record)

# 匯出 Excel
df = pd.DataFrame(records)
df.to_excel(output_file, index=False)
messagebox.showinfo("完成", f"已處理 {len(records)} 份報告，輸出至：\n{output_file}")
