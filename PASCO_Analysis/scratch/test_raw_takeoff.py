import pandas as pd
import numpy as np
from jumpmetrics.core.io import find_frame_when_off_plate
from jumpmetrics.signal_processing.filters import butterworth_filter

df_raw = pd.read_csv("outputs/force/001.csv")
f1 = df_raw.iloc[:, 0]
f2 = df_raw.iloc[:, 1]
total_f = (f1 + f2).dropna().values

fs = 1000
# 測試濾波 vs 原始力量來尋找離地瞬間
takeoff_filtered = find_frame_when_off_plate(
    force_trace=pd.Series(butterworth_filter(arr=total_f, cutoff_frequency=20, fps=fs, padding=fs)),
    sampling_frequency=fs,
    force_threshold=30
)

takeoff_raw = find_frame_when_off_plate(
    force_trace=pd.Series(total_f),
    sampling_frequency=fs,
    force_threshold=10  # 原始數據可能有些雜訊，我們測 10N 或是 30N
)

takeoff_raw_30 = find_frame_when_off_plate(
    force_trace=pd.Series(total_f),
    sampling_frequency=fs,
    force_threshold=30
)

print(f"對照組離地瞬間: 1909")
print(f"濾波力量 (30N閾值) 偵測離地瞬間: {takeoff_filtered}")
print(f"原始力量 (10N閾值) 偵測離地瞬間: {takeoff_raw}")
print(f"原始力量 (30N閾值) 偵測離地瞬間: {takeoff_raw_30}")
