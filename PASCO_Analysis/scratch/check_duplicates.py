import os
import pandas as pd

ref_dir = "refer_results/final"
files = sorted(os.listdir(ref_dir))

records = []
for file in files:
    if not file.endswith('.xlsx'):
        continue
    path = os.path.join(ref_dir, file)
    try:
        df = pd.read_excel(path).set_index("Event")
        if "離地瞬間" in df.columns:
            t_frame = df.loc["Frame", "離地瞬間"]
            s_frame = df.loc["Frame", "動作開始"]
            records.append({"File": file, "Start_Frame": s_frame, "Takeoff_Frame": t_frame})
    except Exception as e:
        print(f"Error {file}: {e}")

df_records = pd.DataFrame(records)
print("=== 參考數據的動作開始與離地瞬間幀數列表 ===")
print(df_records.to_string())
