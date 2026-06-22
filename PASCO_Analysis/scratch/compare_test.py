import pandas as pd

f_out = r"outputs\final\001-1.xlsx"
f_ref = r"refer_results\final\001-1.xlsx"

try:
    df_out = pd.read_excel(f_out)
    print("--- Output File (001-1) ---")
    print(df_out)
except Exception as e:
    print(f"Error reading output: {e}")

try:
    df_ref = pd.read_excel(f_ref)
    print("\n--- Reference File (001-1) ---")
    print(df_ref)
except Exception as e:
    print(f"Error reading reference: {e}")
