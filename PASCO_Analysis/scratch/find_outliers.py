import os
import pandas as pd
import numpy as np

out_dir = "outputs/final"
ref_dir = "refer_results/final"

out_files = set(os.listdir(out_dir))
ref_files = set(os.listdir(ref_dir))

common_files = sorted(list(out_files.intersection(ref_files)))

outliers = []

for file in common_files:
    out_path = os.path.join(out_dir, file)
    ref_path = os.path.join(ref_dir, file)
    
    try:
        df_out = pd.read_excel(out_path).set_index("Event")
        df_ref = pd.read_excel(ref_path).set_index("Event")
        
        # 比較離地瞬間 (takeoff) 的 Frame
        if "離地瞬間" in df_out.columns and "離地瞬間" in df_ref.columns:
            f_out = df_out.loc["Frame", "離地瞬間"]
            f_ref = df_ref.loc["Frame", "離地瞬間"]
            diff = abs(f_out - f_ref)
            
            # 比較動作開始 (start of movement)
            s_out = df_out.loc["Frame", "動作開始"]
            s_ref = df_ref.loc["Frame", "動作開始"]
            sdiff = abs(s_out - s_ref)
            
            if diff > 10 or sdiff > 10:
                outliers.append({
                    "File": file,
                    "Out_Start": s_out,
                    "Ref_Start": s_ref,
                    "Start_Diff": s_out - s_ref,
                    "Out_Takeoff": f_out,
                    "Ref_Takeoff": f_ref,
                    "Takeoff_Diff": f_out - f_ref
                })
    except Exception as e:
        print(f"Error processing {file}: {e}")

df_outliers = pd.DataFrame(outliers)
print("=== 差異較大 (>10 幀) 的檔案列表 ===")
print(df_outliers.to_string(index=False))
