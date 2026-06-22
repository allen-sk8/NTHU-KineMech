import pandas as pd
import numpy as np
import jumpmetrics
from jumpmetrics.core.processors import ForceTimeCurveCMJTakeoffProcessor
from jumpmetrics.core.io import find_frame_when_off_plate
from jumpmetrics.signal_processing.filters import butterworth_filter

df_raw = pd.read_csv("outputs/force/001.csv")
f1 = df_raw.iloc[:, 0]
f2 = df_raw.iloc[:, 1]
total_f = (f1 + f2).dropna().values

fs = 1000
filtered_force = butterworth_filter(arr=total_f, cutoff_frequency=20, fps=fs, padding=fs)
takeoff_frame = find_frame_when_off_plate(force_trace=pd.Series(filtered_force), sampling_frequency=fs, force_threshold=30)

processor = ForceTimeCurveCMJTakeoffProcessor(force_series=pd.Series(filtered_force[:takeoff_frame+1]), sampling_frequency=fs)
processor.get_jump_events()
som = processor.start_of_unweighting_phase

v_orig = processor.velocity_series
s_orig = processor.displacement_series

# 校正
v_corrected = v_orig - v_orig[som]
dt = 1.0 / fs
s_corrected = np.zeros_like(s_orig)
s_corrected[som:] = np.cumsum(0.5 * (v_corrected[som:] + np.roll(v_corrected, 1)[som:]) * dt)

v_corrected[:som] = 0.0
s_corrected[:som] = 0.0
p_corrected = processor.force_series * v_corrected

df_ref = pd.read_excel("refer_results/final/001-1.xlsx").set_index("Event")

print("--- 在對照組的離地瞬間 (Frame 1909) 計算我們的數值 ---")
print(f"對照組 Frame 1909 的值: V-value={df_ref.loc['V-value (m/s)', '離地瞬間']}, S-value={df_ref.loc['S-value (m)', '離地瞬間']}, P-value={df_ref.loc['P-value (W)', '離地瞬間']}")
print(f"我們在 Frame 1909 (校正後) 的值: V-value={v_corrected[1909]:.4f}, S-value={s_corrected[1909]:.4f}, P-value={p_corrected[1909]:.4f}")
print(f"我們在 Frame 1909 (校正前) 的值: V-value={v_orig[1909]:.4f}, S-value={s_orig[1909]:.4f}, P-value={(processor.force_series * v_orig)[1909]:.4f}")
