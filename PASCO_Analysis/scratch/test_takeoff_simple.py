import os
import pandas as pd
import numpy as np

ref_dir = "refer_results/final"
files = sorted(os.listdir(ref_dir))
excluded_files = {"002-1.xlsx", "002-2.xlsx", "002-3.xlsx"}
clean_files = [f for f in files if f.endswith('.xlsx') and f not in excluded_files]

diffs = []

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
        
        # 直接尋找第一個力量小於 10 N 的位置
        custom_takeoff = -1
        for idx in range(len(total_f)):
            if total_f[idx] < 10.0:
                custom_takeoff = idx
                break
                
        diff = custom_takeoff - ref_takeoff
        diffs.append(diff)
        # print(f"{file:<12} | 對照組: {ref_takeoff:5d} | 自訂法: {custom_takeoff:5d} | 差值: {diff:5d}")

diffs = np.array(diffs)
print(f"\n比較完成！樣本數: {len(diffs)}")
print(f"最大絕對差異: {np.max(np.abs(diffs))} 幀")
print(f"平均絕對誤差 (MAE): {np.mean(np.abs(diffs)):.4f} 幀")
print(f"均方根誤差 (RMSE): {np.sqrt(np.mean(diffs**2)):.4f} 幀")
print(f"完全一致 (差0或1幀) 的比例: {np.mean(np.abs(diffs) <= 1) * 100:.2f}%")
