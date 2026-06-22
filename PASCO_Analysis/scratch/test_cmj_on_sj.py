import pandas as pd
import numpy as np
from scipy.signal import butter, filtfilt

class Config:
    fs = 1000
    quiet_phase_max_sec = 1.0
    quiet_phase_buffer_ms = 100
    som_threshold_pct = 0.025
    som_retrograde_window_ms = 250
    takeoff_threshold_n = 10.0
    landing_threshold_n = 30.0
    landing_safety_window_ms = 150
    amortization_before_ms = 45
    amortization_after_ms = 45

config = Config()

def butterworth_filter(arr, cutoff_frequency=20.0, fps=1000.0, padding=1000):
    nyq = 0.5 * fps
    normal_cutoff = cutoff_frequency / nyq
    b, a = butter(4, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, arr)

def find_frame_when_off_plate(force_trace, sampling_frequency, force_threshold):
    # 簡易實作與 CMJ 一致的行為
    for idx in range(len(force_trace)):
        if force_trace[idx] < force_threshold:
            return idx
    return -1

def main():
    csv_file = r"c:\Users\allensk8\vscode-all-in-one\Local_workspace\NTHU-KineMech\PASCO_Analysis\refer_results\sj\SJ CSV 1017\002.csv"
    df = pd.read_csv(csv_file)
    f1 = df.iloc[:, 0]
    f2 = df.iloc[:, 1]
    total_f = (f1 + f2).dropna().values
    
    filtered_force = butterworth_filter(total_f, cutoff_frequency=20.0, fps=1000)
    
    # 1. 離地粗定位
    takeoff_rough = find_frame_when_off_plate(
        force_trace=pd.Series(filtered_force),
        sampling_frequency=config.fs,
        force_threshold=30
    )
    
    # 離地精確點
    takeoff_frame = -1
    for idx in range(max(0, takeoff_rough - 50), len(total_f)):
        if total_f[idx] < config.takeoff_threshold_n:
            takeoff_frame = idx
            break
            
    # 2. 著地精確點
    landing_frame = len(total_f) - 1
    landing_search_start = takeoff_frame + int(config.landing_safety_window_ms * config.fs / 1000)
    for idx in range(landing_search_start, len(total_f)):
        if total_f[idx] > config.landing_threshold_n:
            landing_frame = idx
            break
            
    # 3. 動作開始
    peak_rough = np.argmax(filtered_force[:takeoff_frame])
    max_unweight_rough = np.argmin(filtered_force[:peak_rough])
    
    quiet_samples_limit = int(config.quiet_phase_max_sec * config.fs)
    buffer_samples = int(config.quiet_phase_buffer_ms * config.fs / 1000)
    weight_end = min(quiet_samples_limit, max(0, max_unweight_rough - buffer_samples))
    if weight_end <= 0:
        weight_end = max(1, max_unweight_rough - 50)
        
    bw = np.mean(total_f[:weight_end])
    som_threshold = bw * config.som_threshold_pct
    
    som_frame = -1
    retrograde_samples = int(config.som_retrograde_window_ms * config.fs / 1000)
    search_start = max(0, max_unweight_rough - retrograde_samples)
    for idx in range(max_unweight_rough, search_start - 1, -1):
        if abs(filtered_force[idx] - bw) < som_threshold:
            som_frame = idx + 1
            break
            
    print(f"CMJ Logic results on 002.csv:")
    print(f"  takeoff_rough: {takeoff_rough}")
    print(f"  takeoff_frame: {takeoff_frame}")
    print(f"  landing_frame: {landing_frame}")
    print(f"  peak_rough: {peak_rough}")
    print(f"  max_unweight_rough: {max_unweight_rough}")
    print(f"  weight_end: {weight_end}")
    print(f"  bw: {bw:.2f}")
    print(f"  som_threshold: {som_threshold:.2f}")
    print(f"  search_start: {search_start}")
    print(f"  som_frame: {som_frame} (Ref: 1969, Diff: {som_frame - 1969})")

if __name__ == "__main__":
    main()
