# PASCO 力板數據自動化處理系統 (PASCO-CAP-AutoAnalyzer)

這是一套為實驗室開發的自動化工具，用於將 PASCO 力板的專有格式 `.cap` 檔案批次轉換為標準 CSV 力量數據，並自動分析生成力學指標 Excel 報表。

## 🚀 快速開始

### 1. 環境安裝
本系統需要 Python 3.10+ 環境，請在終端機執行以下指令一鍵安裝所有依賴套件：

```powershell
pip install -r requirements.txt
```

### 2. 操作流程

本系統分為兩個階段，您可以根據需求執行：

#### 階段 A：解析原始數據 (.cap → CSV)
將所有 `.cap` 檔案放入 `inputs/` 資料夾，然後執行：
```powershell
python convert_cap_to_csv.py
```
*   **輸出結果**：將會在 `outputs/force/` 生成各檔案的力量數據 CSV。

#### 階段 B：自動化力學分析 (CSV → Excel)
執行以下指令分析已產出的 CSV 檔案：
```powershell
python analyze_jump_v2.py
```
*   **輸出結果**：將會在 `outputs/final/` 生成實驗室標準格式的 XLSX 報表（包含時間、力量、速度、位移、功率及關鍵事件點）。

---

## 📂 目錄結構說明

- `inputs/`: 放置所有從 PASCO 軟體導出的原始 `.cap` 檔案。
- `outputs/`: 
  - `force/`: 轉換後的原始力量數據 (CSV)。
  - `final/`: 自動分析生成的力學報表 (XLSX)。
- `convert_cap_to_csv.py`: 負責解壓並提取二進位數據的核心腳本。
- `analyze_jump_v2.py`: 調用 `JumpMetrics` 進行 CMJ 分析的計算腳本。
- `PASCO_CAP_Format_and_Conversion_Specs.md`: 技術細節文檔。

---

## ⚠️ 注意事項

1.  **靜止期要求**：受試者在跳躍前必須站在力板上保持靜止至少 **1.1 秒**，系統才能精確計算體重。若靜止期太短，分析腳本會報錯跳過該次實驗。
2.  **力板編號**：腳本會自動辨識力板 EUID。若您發現左右腳順序相反，請修改 `convert_cap_to_csv.py` 中的 `EUID_TO_NAME` 字典。
3.  **錯誤處理**：如果某個 Run 的數據不完整（例如沒有跳躍或離地），該次分析會失敗並顯示在終端機中，不影響其他數據。

---
**開發者**: Antigravity (Advanced Agentic Coding Team)
**版本**: v1.0 (2026-04-27)
