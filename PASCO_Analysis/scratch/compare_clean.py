import os
import pandas as pd
import numpy as np

out_dir = "outputs/final"
ref_dir = "refer_results/final"

out_files = set(os.listdir(out_dir))
ref_files = set(os.listdir(ref_dir))

common_files = sorted(list(out_files.intersection(ref_files)))

# 排除錯誤的對照組檔案 (002-1, 002-2, 002-3)
excluded_files = {"002-1.xlsx", "002-2.xlsx", "002-3.xlsx"}
clean_files = [f for f in common_files if f not in excluded_files]

print(f"原始共同檔案數: {len(common_files)}")
print(f"排除錯誤對照檔案後，乾淨的檔案數: {len(clean_files)}")

comparison_data = {}
event_names = ["動作開始", "最大失重", "制動開始", "重心最低", "最大推蹬力", "離地瞬間", "著地瞬間", "最大離心功率", "最大向心功率", "攤還期開始", "攤還期結束"]
metrics = ["Frame", "Time (s)", "F-value (N)", "S-value (m)", "P-value (W)", "V-value (m/s)"]

for event in event_names:
    comparison_data[event] = {}
    for metric in metrics:
        comparison_data[event][metric] = {"out": [], "ref": []}

for file in clean_files:
    out_path = os.path.join(out_dir, file)
    ref_path = os.path.join(ref_dir, file)
    
    try:
        df_out = pd.read_excel(out_path).set_index("Event")
        df_ref = pd.read_excel(ref_path).set_index("Event")
        
        # 為了保險，確保 Event 是 index
        # 有時候第一欄名稱在 read_excel 時會是 "index" 或是 "Event"，我們先重命名 index
        df_out.index.name = "Event"
        df_ref.index.name = "Event"
        
        for event in event_names:
            if event in df_out.columns and event in df_ref.columns:
                for metric in metrics:
                    if metric in df_out.index and metric in df_ref.index:
                        val_out = df_out.loc[metric, event]
                        val_ref = df_ref.loc[metric, event]
                        
                        if pd.notna(val_out) and pd.notna(val_ref):
                            comparison_data[event][metric]["out"].append(float(val_out))
                            comparison_data[event][metric]["ref"].append(float(val_ref))
    except Exception as e:
        print(f"處理 {file} 時發生錯誤: {e}")

# 計算統計指標
results_summary = []
for event in event_names:
    for metric in metrics:
        outs = np.array(comparison_data[event][metric]["out"])
        refs = np.array(comparison_data[event][metric]["ref"])
        
        if len(outs) > 0:
            diffs = outs - refs
            mae = np.mean(np.abs(diffs))
            rmse = np.sqrt(np.mean(diffs**2))
            mean_diff = np.mean(diffs)
            
            if len(outs) > 1 and np.std(outs) > 0 and np.std(refs) > 0:
                r = np.corrcoef(outs, refs)[0, 1]
            else:
                r = np.nan
                
            results_summary.append({
                "Event": event,
                "Metric": metric,
                "N": len(outs),
                "Mean_Out": np.mean(outs),
                "Mean_Ref": np.mean(refs),
                "Mean_Diff": mean_diff,
                "MAE": mae,
                "RMSE": rmse,
                "Correlation_r": r
            })

df_summary = pd.DataFrame(results_summary)
df_summary.to_csv("scratch/comparison_clean_summary.csv", index=False, encoding="utf-8-sig")

# 印出 Frame 誤差摘要
print("\n=== [排除 002 後] 各事件 Frame 誤差摘要 (單位: 幀, 1幀 = 1毫秒) ===")
df_frame = df_summary[df_summary["Metric"] == "Frame"]
for idx, row in df_frame.iterrows():
    print(f"事件: {row['Event']:<10} | 樣本數: {row['N']:<3} | MAE: {row['MAE']:6.2f} 幀 | RMSE: {row['RMSE']:6.2f} 幀 | r: {row['Correlation_r']:6.4f}")

# 也印出其它重要物理指標的誤差摘要 (如 F-value, S-value, P-value, V-value)
print("\n=== [排除 002 後] 離地瞬間 (Takeoff) 各項物理指標誤差 ===")
df_takeoff = df_summary[df_summary["Event"] == "離地瞬間"]
for idx, row in df_takeoff.iterrows():
    print(f"指標: {row['Metric']:<12} | MAE: {row['MAE']:10.4f} | RMSE: {row['RMSE']:10.4f} | r: {row['Correlation_r']:6.4f}")
