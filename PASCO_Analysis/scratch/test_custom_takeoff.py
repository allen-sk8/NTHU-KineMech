import os
import pandas as pd
import numpy as np

ref_dir = "refer_results/final"
files = sorted(os.listdir(ref_dir))
excluded_files = {"002-1.xlsx", "002-2.xlsx", "002-3.xlsx"}
clean_files = [f for f in files if f.endswith('.xlsx') and f not in excluded_files]

for file in clean_files:
    ref_path = os.path.join(ref_dir, file)
    csv_name = file.split("-")[0] + ".csv"
    raw_path = os.path.join("outputs/force", csv_name)
    
    if os.path.exists(ref_path) and os.path.exists(raw_path):
        df_ref = pd.read_excel(ref_path).set_index("Event")
        ref_takeoff = int(df_ref.loc["Frame", "離地瞬間"])
        
        df_raw = pd.read_csv(raw_path)
        run_num = int(file.split("-")[1].split(".")[0])
        f1 = df_raw.iloc[:, (run_num-1)*2]
        f2 = df_raw.iloc[:, (run_num-1)*2+1]
        total_f = (f1 + f2).dropna().values
        
        peak_idx = np.argmax(total_f)
        
        custom_takeoff = -1
        for idx in range(peak_idx, len(total_f)):
            if total_f[idx] < 10.0:
                custom_takeoff = idx
                break
                
        diff = custom_takeoff - ref_takeoff
        if abs(diff) > 5:
            print(f"{file:<12} | 對照組: {ref_takeoff:5d} | 自訂法: {custom_takeoff:5d} | 差值: {diff:5d} | Peak: {peak_idx:5d} | TotalLen: {len(total_f):5d}")
