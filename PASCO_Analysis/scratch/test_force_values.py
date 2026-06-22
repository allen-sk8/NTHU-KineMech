import pandas as pd
import numpy as np
from jumpmetrics.signal_processing.filters import butterworth_filter

df_raw = pd.read_csv("outputs/force/001.csv")
f1 = df_raw.iloc[:, 0]
f2 = df_raw.iloc[:, 1]
total_f = (f1 + f2).dropna().values

fs = 1000
filtered_force = butterworth_filter(arr=total_f, cutoff_frequency=20, fps=fs, padding=fs)

print(f"原本力量 (無濾波) 在 1909 幀: {total_f[1909]:.2f} N")
print(f"原本力量 (無濾波) 在 1929 幀: {total_f[1929]:.2f} N")
print(f"濾波後力量在 1909 幀: {filtered_force[1909]:.2f} N")
print(f"濾波後力量在 1929 幀: {filtered_force[1929]:.2f} N")
