import pandas as pd

f_out = r"outputs\final\001-1.xlsx"
f_ref = r"refer_results\final\001-1.xlsx"

df_out = pd.read_excel(f_out).set_index("Event")
df_ref = pd.read_excel(f_ref).set_index("Event")

# 合併並對比
combined = {}
for col in df_out.columns:
    combined[f"Out_{col}"] = df_out[col]
    combined[f"Ref_{col}"] = df_ref[col]

df_combined = pd.DataFrame(combined)
# 重新排列欄位讓 out 和 ref 相鄰
ordered_cols = []
for col in df_out.columns:
    ordered_cols.extend([f"Out_{col}", f"Ref_{col}"])
df_combined = df_combined[ordered_cols]

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)
pd.set_option('display.width', 1000)

print(df_combined)
