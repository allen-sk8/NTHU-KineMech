import os
import pandas as pd
import numpy as np

ref_dir = "refer_results/final"
files = ["004-3.xlsx", "006-2.xlsx", "007-2.xlsx", "011-2.xlsx", "011-3.xlsx", "013-1.xlsx", "013-2.xlsx", "013-3.xlsx", "014-1.xlsx", "014-2.xlsx", "017-2.xlsx", "017-3.xlsx"]

for file in files:
    ref_path = os.path.join(ref_dir, file)
    csv_name = file.split("-")[0] + ".csv"
    raw_path = os.path.join("outputs/force", csv_name)
    
    if os.path.exists(ref_path) and os.path.exists(raw_path):
        df_ref = pd.read_excel(ref_path).set_index("Event")
        ref_pf = int(df_ref.loc["Frame", "最大推蹬力"])
        ref_braking = int(df_ref.loc["Frame", "制動開始"])
        ref_takeoff = int(df_ref.loc["Frame", "離地瞬間"])
        
        df_raw = pd.read_csv(raw_path)
        run_num = int(file.split("-")[1].split(".")[0])
        f1 = df_raw.iloc[:, (run_num-1)*2]
        f2 = df_raw.iloc[:, (run_num-1)*2+1]
        total_f = (f1 + f2).dropna().values
        
        # 在制動開始到離地瞬間區間尋找最大值
        custom_pf = np.argmax(total_f[ref_braking:ref_takeoff]) + ref_braking
        
        print(f"{file:<12} | 對照組: {ref_pf} | 自訂區間最大值: {custom_pf} | 差值: {custom_pf - ref_pf}")
