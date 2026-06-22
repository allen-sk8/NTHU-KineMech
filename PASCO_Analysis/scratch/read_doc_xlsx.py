import os
import pandas as pd

def main():
    doc_path = r"c:\Users\allensk8\vscode-all-in-one\Local_workspace\NTHU-KineMech\PASCO_Analysis\jump_metrics_documentation.xlsx"
    if not os.path.exists(doc_path):
        print(f"File {doc_path} does not exist")
        return
        
    xl = pd.ExcelFile(doc_path)
    df = xl.parse("Details").set_index("Event")
    
    print("--- Event Documentation ---")
    for col in df.columns:
        print(f"\n[Event: {col}]")
        print(df[col].to_string())

if __name__ == "__main__":
    main()
