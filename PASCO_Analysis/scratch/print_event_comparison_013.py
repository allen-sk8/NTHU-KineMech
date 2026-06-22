import pandas as pd

df_out = pd.read_excel("outputs/final/013-1.xlsx").set_index("Event")
df_ref = pd.read_excel("refer_results/final/013-1.xlsx").set_index("Event")

print("Event | Out Frame | Ref Frame")
print("-" * 30)
for event in df_ref.columns:
    if event in df_out.columns:
        print(f"{event:<10} | {df_out.loc['Frame', event]:9.1f} | {df_ref.loc['Frame', event]:9.1f}")
