import os
import pandas as pd
import numpy as np
from scipy.signal import butter, filtfilt

class Config:
    fs = 1000
    takeoff_threshold_n = 10.0
    landing_threshold_n = 30.0
    landing_safety_window_ms = 150

config = Config()

def butterworth_filter(arr, cutoff_frequency=20.0, fps=1000.0, padding=1000):
    nyq = 0.5 * fps
    normal_cutoff = cutoff_frequency / nyq
    b, a = butter(4, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, arr)

def find_frame_when_off_plate(force_trace, sampling_frequency, force_threshold):
    for idx in range(len(force_trace)):
        if force_trace[idx] < force_threshold:
            return idx
    return -1

def main():
    excel_dir = r"c:\Users\allensk8\vscode-all-in-one\Local_workspace\NTHU-KineMech\PASCO_Analysis\refer_results\sj\SJ Excel"
    csv_dir = r"c:\Users\allensk8\vscode-all-in-one\Local_workspace\NTHU-KineMech\PASCO_Analysis\refer_results\sj\SJ CSV 1017"
    
    files = sorted([f for f in os.listdir(excel_dir) if f.endswith('.xlsx')])
    
    trials_data = []
    for f in files:
        csv_name = f.replace("-1.xlsx", ".csv").replace("-2.xlsx", ".csv").replace("-3.xlsx", ".csv")
        csv_path = os.path.join(csv_dir, csv_name)
        excel_path = os.path.join(excel_dir, f)
        
        if not os.path.exists(csv_path):
            continue
            
        try:
            xl = pd.ExcelFile(excel_path)
            df_details = xl.parse("Details").set_index("Event")
            ref_som = float(df_details.loc["Frame", "動作開始"])
            ref_takeoff = float(df_details.loc["Frame", "離地瞬間"])
            ref_peak = float(df_details.loc["Frame", "最大推蹬力"])
            
            df_csv = pd.read_csv(csv_path)
            if "-1.xlsx" in f:
                col_idx = 0
            elif "-2.xlsx" in f:
                col_idx = 2
            else:
                col_idx = 4
                
            f1 = df_csv.iloc[:, col_idx]
            f2 = df_csv.iloc[:, col_idx + 1]
            total_f = (f1 + f2).dropna().values
            
            # 過濾掉異常 trial
            if ref_som < 500:
                continue
                
            trials_data.append({
                "file": f,
                "total_f": total_f,
                "ref_som": ref_som,
                "ref_takeoff": ref_takeoff,
                "ref_peak": ref_peak
            })
        except:
            pass
            
    print(f"Loaded {len(trials_data)} valid trials (excluding som < 500).")
    
    errors_1 = []
    errors_2 = []
    
    for trial in trials_data:
        total_f = trial["total_f"]
        ref_som = trial["ref_som"]
        
        filtered_force = butterworth_filter(total_f, cutoff_frequency=20.0, fps=1000)
        
        # 1. 離地瞬間
        takeoff_rough = find_frame_when_off_plate(filtered_force, config.fs, 30.0)
        takeoff_frame = -1
        for idx in range(max(0, takeoff_rough - 50), len(total_f)):
            if total_f[idx] < config.takeoff_threshold_n:
                takeoff_frame = idx
                break
        if takeoff_frame == -1:
            takeoff_frame = takeoff_rough
            
        # 2. 推蹬峰值
        peak_rough = np.argmax(filtered_force[:takeoff_frame])
        
        # 3. 初始體重
        bw_init = np.mean(total_f[:1000])
        som_threshold = bw_init * 0.025
        
        # 4. Method 1 (CMJ Default with 1s window)
        search_start_idx = max(0, peak_rough - 1000)
        max_unweight_rough = np.argmin(filtered_force[search_start_idx : peak_rough]) + search_start_idx
        retrograde_samples = int(250 * config.fs / 1000)
        search_limit = max(0, max_unweight_rough - retrograde_samples)
        som_1 = -1
        for idx in range(max_unweight_rough, search_limit - 1, -1):
            if abs(filtered_force[idx] - bw_init) < som_threshold:
                som_1 = idx + 1
                break
        if som_1 == -1:
            som_1 = search_limit
        errors_1.append(abs(som_1 - ref_som))
        
        # 5. Method 2 (Peak backward first < 2.5% BW)
        som_2 = -1
        for idx in range(peak_rough, 0, -1):
            if filtered_force[idx] < bw_init + som_threshold:
                som_2 = idx + 1
                break
        if som_2 == -1:
            som_2 = 0
        errors_2.append(abs(som_2 - ref_som))
        
    print(f"\nMethod 1 (CMJ with 1s Window) MAE: {np.mean(errors_1):.2f} frames ({np.mean(errors_1):.2f} ms)")
    print(f"Method 2 (Peak backward) MAE: {np.mean(errors_2):.2f} frames ({np.mean(errors_2):.2f} ms)")

if __name__ == "__main__":
    main()
