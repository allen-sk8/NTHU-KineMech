import pandas as pd
import numpy as np
from jumpmetrics.signal_processing.filters import butterworth_filter

df_raw = pd.read_csv("outputs/force/001.csv")
f1 = df_raw.iloc[:, 0]
f2 = df_raw.iloc[:, 1]
total_f = (f1 + f2).dropna().values

fs = 1000
filtered_force = butterworth_filter(arr=total_f, cutoff_frequency=20, fps=fs, padding=fs)

print("Frame | Raw Force (N) | Filtered Force (N)")
print("-" * 43)
for idx in range(1900, 1925):
    print(f"{idx:5d} | {total_f[idx]:13.2f} | {filtered_force[idx]:18.2f}")
