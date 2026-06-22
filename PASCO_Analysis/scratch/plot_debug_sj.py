import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt
import os

def butterworth_filter(arr, cutoff_frequency=20.0, fps=1000.0, padding=1000):
    nyq = 0.5 * fps
    normal_cutoff = cutoff_frequency / nyq
    b, a = butter(4, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, arr)

def plot_file(file_name, ref_som, ref_peak, ref_takeoff, ref_landing, save_name):
    csv_file = f"c:\\Users\\allensk8\\vscode-all-in-one\\Local_workspace\\NTHU-KineMech\\PASCO_Analysis\\refer_results\\sj\\SJ CSV 1017\\{file_name}"
    df = pd.read_csv(csv_file)
    f1 = df.iloc[:, 0]
    f2 = df.iloc[:, 1]
    total_f = (f1 + f2).dropna().values
    
    filtered_force = butterworth_filter(total_f, cutoff_frequency=20.0, fps=1000)
    
    plt.figure(figsize=(12, 6))
    plt.plot(total_f, label='Raw Force', alpha=0.3)
    plt.plot(filtered_force, label='Filtered Force', color='black')
    
    # 標記對照組事件
    plt.axvline(ref_som, color='green', linestyle='--', label=f'Ref SoM ({ref_som})')
    plt.axvline(ref_peak, color='blue', linestyle='--', label=f'Ref Peak ({ref_peak})')
    plt.axvline(ref_takeoff, color='red', linestyle='--', label=f'Ref Takeoff ({ref_takeoff})')
    plt.axvline(ref_landing, color='purple', linestyle='--', label=f'Ref Landing ({ref_landing})')
    
    # 體重基準線
    bw = np.mean(total_f[:1000])
    plt.axhline(bw, color='orange', linestyle=':', label=f'BW ({bw:.1f} N)')
    
    plt.xlim(max(0, ref_som - 200), min(len(total_f), ref_landing + 200))
    plt.title(f"SJ Events Verification - {file_name}")
    plt.legend()
    plt.grid(True)
    os.makedirs("scratch", exist_ok=True)
    plt.savefig(f"scratch/{save_name}")
    plt.close()
    print(f"Saved debug plot to scratch/{save_name}")

def main():
    plot_file("001.csv", 1168, 1352, 1450, 2017, "sj_debug_001.png")
    plot_file("002.csv", 1969, 2361, 2446, 2966, "sj_debug_002.png")

if __name__ == "__main__":
    main()
