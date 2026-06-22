import os
import pandas as pd

def main():
    excel_file = r"c:\Users\allensk8\vscode-all-in-one\Local_workspace\NTHU-KineMech\PASCO_Analysis\refer_results\cmj\final\001-1.xlsx"
    if os.path.exists(excel_file):
        df = pd.read_excel(excel_file, sheet_name="CMJ", header=None)
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 1000)
        print("--- CMJ Sheet ---")
        print(df)
    else:
        print("CMJ ref file does not exist")

if __name__ == "__main__":
    main()
