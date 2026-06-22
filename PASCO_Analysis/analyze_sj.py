import os
import argparse

def main():
    parser = argparse.ArgumentParser(description="PASCO SJ (無蹲跳) 垂直跳躍分析工具 [開發中/佔位符]")
    args = parser.parse_args()
    
    input_dir = 'outputs/force/sj'
    output_dir = 'outputs/final/sj'
    plot_dir = 'outputs/plots/sj'
    
    print("==================================================")
    print("    PASCO SJ (Squat Jump) 垂直跳躍分析模組")
    print("==================================================")
    print(f"預設輸入路徑 (CSV 力量): {input_dir}")
    print(f"預設輸出路徑 (雙 Sheet Excel): {output_dir}")
    print(f"預設圖表路徑 (診斷圖): {plot_dir}")
    print("\n【開發提示說明】:")
    print("1. SJ (Squat Jump) 的動作開始判定與 CMJ 不同，SJ 沒有下蹲準備期 (Countermovement Phase)。")
    print("2. 動作開始 (SoM) 判定通常直接基於力量偏離體重 (BW) 突破向上推蹬的一刻。")
    print("3. 請參考 metrics_calculator.py 與 analyze_cmj.py 結構，未來可在此處實作 SJ 專屬之特徵事件定位器。")
    print("==================================================")

if __name__ == "__main__":
    main()
