import pandas as pd
import numpy as np
from jumpmetrics.signal_processing.filters import butterworth_filter

df_raw = pd.read_csv("outputs/force/013.csv")
# Run 1 的雙力板總和
f1 = df_raw.iloc[:, 0]
f2 = df_raw.iloc[:, 1]
total_f = (f1 + f2).dropna().values

fs = 1000
filtered_force = butterworth_filter(arr=total_f, cutoff_frequency=20, fps=fs, padding=fs)

# 對照組的離地瞬間 (Takeoff) 
# 我們看看對照組的 013-1.xlsx 裡面的 Event: 離地瞬間
# 從剛剛 check_duplicates.py 的輸出：
# 013-1.xlsx 的 Takeoff_Frame 是 2233
# 所以離地瞬間在 2233 幀。

# 印出 1879 幀 (對照組的最大推蹬力) 和 2151 幀 (我們程式的最大推蹬力) 的力量值
print("1879 幀 (對照組判定最大推蹬力):")
print(f"  原始力量 = {total_f[1879]:.2f} N")
print(f"  濾波力量 = {filtered_force[1879]:.2f} N")

print("\n2151 幀 (我們的程式判定最大推蹬力):")
print(f"  原始力量 = {total_f[2151]:.2f} N")
print(f"  濾波力量 = {filtered_force[2151]:.2f} N")

# 在離地瞬間 (2233 幀) 之前，原始力量與濾波力量的最大值分別在哪裡？
# 我們通常會在 SoM (約 1246 幀) 到 離地瞬間 (2233 幀) 之間找最大推蹬力。
som = 1246
takeoff = 2233

raw_max_idx = np.argmax(total_f[som:takeoff]) + som
filt_max_idx = np.argmax(filtered_force[som:takeoff]) + som

print(f"\n從 SoM ({som}) 到 Takeoff ({takeoff}) 區間：")
print(f"  原始力量最大值出現在 Frame {raw_max_idx}，力量為 {total_f[raw_max_idx]:.2f} N")
print(f"  濾波力量最大值出現在 Frame {filt_max_idx}，力量為 {filtered_force[filt_max_idx]:.2f} N")
