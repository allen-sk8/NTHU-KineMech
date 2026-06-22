import pandas as pd
import numpy as np
from scipy.signal import butter, filtfilt

def butterworth_filter(arr, cutoff_frequency=20.0, fps=1000.0, padding=1000):
    nyq = 0.5 * fps
    normal_cutoff = cutoff_frequency / nyq
    b, a = butter(4, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, arr)

def test_file(file_name, ref_som, ref_takeoff, ref_peak):
    csv_file = f"c:\\Users\\allensk8\\vscode-all-in-one\\Local_workspace\\NTHU-KineMech\\PASCO_Analysis\\refer_results\\sj\\SJ CSV 1017\\{file_name}"
    df = pd.read_csv(csv_file)
    f1 = df.iloc[:, 0]
    f2 = df.iloc[:, 1]
    total_f = (f1 + f2).dropna().values
    
    filtered_force = butterworth_filter(total_f, cutoff_frequency=20.0, fps=1000)
    
    # 離地瞬間
    takeoff_rough = np.argmin(filtered_force) # 粗定位
    # 往回找
    takeoff_frame = -1
    for idx in range(max(0, takeoff_rough - 100), len(total_f)):
        if total_f[idx] < 10.0:
            takeoff_frame = idx
            break
            
    # 靜止期：前 1.0 秒
    bw = np.mean(total_f[:1000])
    som_threshold = bw * 0.025
    
    # 從離地前最大力量往回搜尋
    peak_force_frame = np.argmax(filtered_force[:takeoff_frame])
    
    # 尋找第一個向上突破 bw + som_threshold 的點
    # 也就是說，在此點之後力量大於 bw + som_threshold，且往回搜尋到小於該閾值的點
    som_frame_pred = -1
    for idx in range(peak_force_frame, 0, -1):
        if filtered_force[idx] < bw + som_threshold:
            som_frame_pred = idx + 1
            break
            
    print(f"File: {file_name}")
    print(f"  Calculated BW: {bw:.4f} N (Weight: {bw/9.81:.2f} kg)")
    print(f"  Peak Force Frame: Pred={peak_force_frame}, Ref={ref_peak}")
    print(f"  Takeoff Frame: Pred={takeoff_frame}, Ref={ref_takeoff}")
    print(f"  SoM Frame: Pred={som_frame_pred}, Ref={ref_som} (Diff: {som_frame_pred - ref_som})")
    
    # 測試如果我們微調靜止期 (例如 SoM 往前 500 幀) 來重新計算 bw 呢？
    # 在 SJ 中，因為 SoM 前是靜止蹲姿，如果我們用 [0:som_frame_pred-200] 重新計算 bw，會不會更準？
    if som_frame_pred != -1:
        weight_end = max(100, som_frame_pred - 200)
        bw_refined = np.mean(total_f[:weight_end])
        som_threshold_refined = bw_refined * 0.025
        # 重新搜尋 SoM
        som_frame_pred_ref = -1
        for idx in range(peak_force_frame, 0, -1):
            if filtered_force[idx] < bw_refined + som_threshold_refined:
                som_frame_pred_ref = idx + 1
                break
        print(f"  Refined BW (up to {weight_end}): {bw_refined:.4f} N")
        print(f"  Refined SoM: Pred={som_frame_pred_ref} (Diff: {som_frame_pred_ref - ref_som})")

def main():
    test_file("001.csv", 1168, 1450, 1352)
    test_file("002.csv", 1969, 2446, 2361)

if __name__ == "__main__":
    main()
