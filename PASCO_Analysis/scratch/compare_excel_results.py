import os
import pandas as pd
import numpy as np

def compare_file(trial_id):
    ref_path = f"refer_results/sj/SJ Excel/{trial_id}.xlsx"
    our_path = f"outputs/sj/SJ 原始/{trial_id.split('-')[0]}/{trial_id}.xlsx"
    
    if not os.path.exists(ref_path) or not os.path.exists(our_path):
        print(f"File missing for {trial_id}")
        return
        
    print(f"\n=================== COMPARING {trial_id} ===================")
    
    # Compare Details
    try:
        ref_details = pd.read_excel(ref_path, sheet_name="Details").set_index("Event")
        our_details = pd.read_excel(our_path, sheet_name="Details").set_index("Event")
        
        # 對齊 index 和 columns
        events = ["動作開始", "最大推蹬力", "離地瞬間", "著地瞬間", "最大向心功率"]
        cols = ["Frame", "Time (s)", "F-value (N)", "S-value (m)", "P-value (W)", "V-value (m/s)"]
        
        print("\n[Details Sheet Comparison (Our / Ref)]")
        for ev in events:
            print(f"\n  Event: {ev}")
            for c in cols:
                ref_val = ref_details.loc[c, ev] if ev in ref_details.columns and c in ref_details.index else np.nan
                our_val = our_details.loc[c, ev] if ev in our_details.columns and c in our_details.index else np.nan
                diff = our_val - ref_val if not np.isnan(our_val) and not np.isnan(ref_val) else np.nan
                print(f"    {c:15s} | Our: {our_val:10.4f} | Ref: {ref_val:10.4f} | Diff: {diff:+.4f}")
    except Exception as e:
        print(f"Error comparing Details for {trial_id}: {e}")
        
    # Compare SJ sheet
    try:
        ref_sj = pd.read_excel(ref_path, sheet_name="SJ")
        our_sj = pd.read_excel(our_path, sheet_name="SJ")
        
        # 對齊 header
        # 我們跳過大標題行 (Row 0)，直接比較 Row 1 (Header), Row 2 (原始), Row 3 (%標準化)
        print("\n[SJ Sheet Comparison (Our / Ref)]")
        for col_idx in range(1, ref_sj.shape[1]):
            col_name = ref_sj.iloc[0, col_idx]
            
            ref_raw = ref_sj.iloc[1, col_idx]
            our_raw = our_sj.iloc[1, col_idx]
            diff_raw = float(our_raw) - float(ref_raw) if isinstance(our_raw, (int, float)) and isinstance(ref_raw, (int, float)) else np.nan
            
            ref_std = ref_sj.iloc[2, col_idx]
            our_std = our_sj.iloc[2, col_idx]
            diff_std = float(our_std) - float(ref_std) if isinstance(our_std, (int, float)) and isinstance(ref_std, (int, float)) else np.nan
            
            print(f"\n  Metric: {col_name}")
            print(f"    原始    | Our: {our_raw} | Ref: {ref_raw} | Diff: {diff_raw:+.4f}")
            print(f"    %標準化 | Our: {our_std} | Ref: {ref_std} | Diff: {diff_std:+.4f}")
    except Exception as e:
        print(f"Error comparing SJ sheet for {trial_id}: {e}")

def main():
    compare_file("001-1")
    compare_file("002-2")

if __name__ == "__main__":
    main()
