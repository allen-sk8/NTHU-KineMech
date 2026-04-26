# Gait Analysis Data Extractor (步態分析資料提取工具)

本工具專為自動化處理步態分析 PDF 報告而設計。它可以從大量的 PDF 報告中精確提取受試者資訊、步態穩定度、擺動角度以及步態相位等參數，並將其匯整為單一 Excel 報表，大幅節省手動輸入的時間。

## ✨ 主要功能
- **批量處理**: 一次解析整個資料夾內的所有 PDF 檔案。
- **高精度提取**: 針對特定報告格式優化，準確識別左/右腳數據。
- **GUI 介面**: 提供圖形化介面（App 版本），方便非技術人員操作。
- **數據彙整**: 自動產生 `summary.xlsx`，方便後續統計分析。

## 📊 提取參數包含：
- **基本資訊**: 姓名、日期、身高、體重、性別、年齡。
- **步態類型**: Supination, Pronation, OverPronation (左/右)。
- **穩定度 (Stability)**: 穩定百分比、平均擺動角 (Sway Angle)。
- **時間相位**: 支撐相 (Stance Phase)、擺動相 (Swing Phase) 時間比。
- **動力學平衡**: 角度平衡、力量平衡。

## 🚀 使用說明

### 1. 準備資料
將所有 PDF 報告放入 `02_Gait_Report_Extractor/data` 資料夾。

### 2. 執行工具
你可以選擇執行純腳本或圖形化 App：
- **執行腳本**:
  ```bash
  python extract_pdf.py
  ```
- **執行 GUI App**:
  直接執行 `extract_pdf_app.exe` 或執行：
  ```bash
  python extract_pdf_app.py
  ```

### 3. 查看結果
執行完成後，根目錄會生成 `summary.xlsx`。

## 🛠 技術棧
- **pdfplumber**: 用於 PDF 文字提取。
- **Regex (正規表達式)**: 用於複雜數據匹配。
- **Pandas**: 資料處理與 Excel 匯出。
- **Tkinter**: GUI 介面開發。

---
*Developed by Allen @ NTHU-KineMech Lab*
