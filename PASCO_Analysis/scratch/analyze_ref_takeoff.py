import os
import pandas as pd
import numpy as np

ref_dir = "refer_results/final"
files = ["001-1.xlsx", "003-1.xlsx", "005-1.xlsx", "006-1.xlsx", "007-1.xlsx"]

for file in files:
    ref_path = os.path.join(ref_dir, file)
    csv_name = file.split("-")[0] + ".csv"
    raw_path = os.path.join("outputs/force", csv_name)
    
    if os.path.exists(ref_path) and os.path.exists(raw_path):
        df_ref = pd.read_excel(ref_path).set_index("Event")
        ref_frame = int(df_ref.loc["Frame", "離地瞬間"])
        
        df_raw = pd.read_csv(raw_path)
        # 取得對應 Run 的雙力板總和
        # 檔名如果是 001-1.xlsx，對應 Run 1
        run_num = int(file.split("-")[1].split(".")[0])
        f1 = df_raw.iloc[:, (run_num-1)*2]
        f2 = df_raw.iloc[:, (run_num-1)*2+1]
        total_f = (f1 + f2).dropna().values
        
        # 印出對照組離地瞬間前後幾幀的原始力量
        print(f"\n檔案: {file} | 對照組判定離地瞬間: {ref_frame}")
        for offset in range(-2, 3):
            idx = ref_frame + offset
            if 0 <= idx < len(total_f):
                print(f"  Frame {idx}: Raw Force = {total_f[idx]:.2f} N")
