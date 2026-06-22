import os
import pandas as pd
import numpy as np

out_dir = "outputs/final"
ref_dir = "refer_results/final"

out_files = set(os.listdir(out_dir))
ref_files = set(os.listdir(ref_dir))

common_files = sorted(list(out_files.intersection(ref_files)))
excluded_files = {"002-1.xlsx", "002-2.xlsx", "002-3.xlsx"}
clean_files = [f for f in common_files if f not in excluded_files]

large_diffs = []

for file in clean_files:
    out_path = os.path.join(out_dir, file)
    ref_path = os.path.join(ref_dir, file)
    
    try:
        df_out = pd.read_excel(out_path).set_index("Event")
        df_ref = pd.read_excel(ref_path).set_index("Event")
        
        o_pf = df_out.loc["Frame", "最大推蹬力"]
        r_pf = df_ref.loc["Frame", "最大推蹬力"]
        diff = abs(o_pf - r_pf)
        
        if diff > 10:
            large_diffs.append({
                "File": file,
                "Out_PeakForce": o_pf,
                "Ref_PeakForce": r_pf,
                "Diff": o_pf - r_pf,
                "Out_Fval": df_out.loc["F-value (N)", "最大推蹬力"],
                "Ref_Fval": df_ref.loc["F-value (N)", "最大推蹬力"]
            })
    except Exception as e:
        print(f"Error {file}: {e}")

df_large = pd.DataFrame(large_diffs)
print("=== 最大推蹬力差異大於 10 幀的檔案 ===")
print(df_large.to_string(index=False))
