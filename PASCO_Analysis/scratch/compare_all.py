import os
import pandas as pd
import numpy as np

out_dir = "outputs/final"
ref_dir = "refer_results/final"

out_files = set(os.listdir(out_dir))
ref_files = set(os.listdir(ref_dir))

common_files = sorted(list(out_files.intersection(ref_files)))
print(f"找到 {len(common_files)} 個共同的檔案進行比較。")

# 用來收集所有事件的所有指標數據
# 結構：{event: {metric: {"out": [], "ref": []}}}
comparison_data = {}

event_names = ["動作開始", "最大失重", "制動開始", "重心最低", "最大推蹬力", "離地瞬間", "著地瞬間", "最大離心功率", "最大向心功率", "攤還期開始", "攤還期結束"]
metrics = ["Frame", "Time (s)", "F-value (N)", "S-value (m)", "P-value (W)", "V-value (m/s)"]

for event in event_names:
    comparison_data[event] = {}
    for metric in metrics:
        comparison_data[event][metric] = {"out": [], "ref": []}

for file in common_files:
    out_path = os.path.join(out_dir, file)
    ref_path = os.path.join(ref_dir, file)
    
    try:
        df_out = pd.read_excel(out_path)
        df_ref = pd.read_excel(ref_path)
        
        # 轉置後，讓 Event 成為欄位名以便提取
        # 原始格式中，Event 是 row 標籤或第一欄的值
        # 我們檢查 compare_test.py 的輸出：
        # Output File 的第一行 (index=0) 是 Frame，但 columns 是 Event，然後內容是:
        # Event 動作開始 ... 攤還期開始 攤還期結束
        # 0 Frame 1157.0 ... 1609.0 1695.0
        # 這是轉置過後的 DataFrame (在 analyze_jump_v2.py 中 122 行：res_df.T.reset_index())
        # 所以它的第一欄叫做 "index"，內容是 "Frame", "Time (s)", "F-value (N)" ...
        # 其他欄位名稱就是事件名稱 ("動作開始" 等)
        
        # 為了保險起見，我們將第一欄設為 index
        df_out_clean = df_out.set_index(df_out.columns[0])
        df_ref_clean = df_ref.set_index(df_ref.columns[0])
        
        for event in event_names:
            if event in df_out_clean.columns and event in df_ref_clean.columns:
                for metric in metrics:
                    if metric in df_out_clean.index and metric in df_ref_clean.index:
                        val_out = df_out_clean.loc[metric, event]
                        val_ref = df_ref_clean.loc[metric, event]
                        
                        # 排除 NaN
                        if pd.notna(val_out) and pd.notna(val_ref):
                            comparison_data[event][metric]["out"].append(float(val_out))
                            comparison_data[event][metric]["ref"].append(float(val_ref))
    except Exception as e:
        print(f"處理檔案 {file} 時發生錯誤: {e}")

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
            
            # 計算相關係數
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
df_summary.to_csv("scratch/comparison_summary.csv", index=False, encoding="utf-8-sig")

# 印出摘要 (特別針對 Frame 的誤差，看看差幾幀)
print("\n=== 各事件 Frame 誤差摘要 (單位: 幀, 1幀 = 1毫秒) ===")
df_frame = df_summary[df_summary["Metric"] == "Frame"]
for idx, row in df_frame.iterrows():
    print(f"事件: {row['Event']:<10} | 樣本數: {row['N']:<3} | MAE: {row['MAE']:6.2f} 幀 | RMSE: {row['RMSE']:6.2f} 幀 | r: {row['Correlation_r']:6.4f}")
