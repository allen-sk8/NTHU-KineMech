import pandas as pd
import numpy as np
from scipy.signal import butter, filtfilt

def butterworth_filter(arr, cutoff_frequency=20.0, fps=1000.0, padding=1000):
    nyq = 0.5 * fps
    normal_cutoff = cutoff_frequency / nyq
    b, a = butter(4, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, arr)

def check_file(file_name, ref_som):
    csv_file = f"c:\\Users\\allensk8\\vscode-all-in-one\\Local_workspace\\NTHU-KineMech\\PASCO_Analysis\\refer_results\\sj\\SJ CSV 1017\\{file_name}"
    df = pd.read_csv(csv_file)
    f1 = df.iloc[:, 0]
    f2 = df.iloc[:, 1]
    total_f = (f1 + f2).dropna().values
    
    filtered_force = butterworth_filter(total_f, cutoff_frequency=20.0, fps=1000)
    
    bw = np.mean(total_f[:1000])
    
    # 尋找 0 到 ref_som 之間，F_net 絕對值大於不同百分比 bw 的幀
    print(f"--- File: {file_name} ---")
    print(f"BW: {bw:.2f}")
    
    for pct in [0.02, 0.022, 0.024, 0.025, 0.026]:
        threshold = bw * pct
        first_frame = -1
        for idx in range(len(filtered_force)):
            if abs(filtered_force[idx] - bw) > threshold:
                first_frame = idx
                break
        print(f"Threshold PCT: {pct:.3f} ({threshold:.2f} N) -> First Frame Deviating: {first_frame} (Ref: {ref_som}, Diff: {first_frame - ref_som})")

def main():
    check_file("001.csv", 1168)
    check_file("002.csv", 1969)

if __name__ == "__main__":
    main()
