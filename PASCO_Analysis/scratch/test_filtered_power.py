import pandas as pd
import numpy as np
from jumpmetrics.signal_processing.filters import butterworth_filter

df_raw = pd.read_csv("outputs/force/001.csv")
f1 = df_raw.iloc[:, 0]
f2 = df_raw.iloc[:, 1]
total_f = (f1 + f2).dropna().values
fs = 1000

filtered_force = butterworth_filter(arr=total_f, cutoff_frequency=20, fps=fs, padding=fs)

# 對照組 1909 幀離地，1153 幀 SoM
som = 1153
takeoff = 1909
ref_p = -6.61

# 計算速度
from jumpmetrics.core.processors import ForceTimeCurveCMJTakeoffProcessor
processor = ForceTimeCurveCMJTakeoffProcessor(
    force_series=pd.Series(filtered_force[:takeoff+1]),
    sampling_frequency=fs
)
processor.get_jump_events()
v_orig = processor.velocity_series
v_corrected = v_orig - v_orig[som]

print("離地瞬間 1909 幀的功率比較：")
print(f"對照組功率: {ref_p} W")

# 1. 用原始力計算
p_raw = total_f[1909] * v_corrected[1909]
print(f"用原始力計算 (Raw_F * V): {p_raw:.2f} W (誤差: {p_raw - ref_p:.2f} W)")

# 2. 用濾波力計算
p_filt = filtered_force[1909] * v_corrected[1909]
print(f"用濾波力計算 (Filt_F * V): {p_filt:.2f} W (誤差: {p_filt - ref_p:.2f} W)")

# 3. 淨力 (用原始淨力)
p_net_raw = (total_f[1909] - processor.body_weight) * v_corrected[1909]
print(f"用原始淨力計算 (Raw_Fnet * V): {p_net_raw:.2f} W (誤差: {p_net_raw - ref_p:.2f} W)")

# 4. 淨力 (用濾波淨力)
p_net_filt = (filtered_force[1909] - processor.body_weight) * v_corrected[1909]
print(f"用濾波淨力計算 (Filt_Fnet * V): {p_net_filt:.2f} W (誤差: {p_net_filt - ref_p:.2f} W)")
