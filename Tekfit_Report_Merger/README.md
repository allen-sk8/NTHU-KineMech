# IMOTEK Tekfit Report Reader (IMOTEK PDF 資料讀取工具)

本工具專用於讀取並整合 IMOTEK Tekfit 系統生成的 PDF 報告。它特別針對「穩定度」與「偏移量」分析，支援橫跨多種負重/節拍條件（50, 70, 90, 110, free）的數據整合。

## 🎯 目標
將分散在多份 PDF 報告中的數據（通常一個受試者在不同條件下會有多份報告）自動按 ID 與日期合併到同一個 Excel 橫列中，以便進行縱向與橫向對比。

## 📂 處理流程
1. **檔名識別**: 自動解析檔名中的 ID 與測試條件（例如：`free-ID01.pdf`）。
2. **文字提取**: 讀取 PDF 第 1 頁的日期資訊與第 3 頁的穩定度數據。
3. **數據對齊**: 將同一 ID 在不同條件下的數值自動歸類。
4. **Excel 產出**: 生成 `tekfit_merged.xlsx`。

## 📊 整合欄位定義：
- **ID / Date**: 受試者編號與測試日期。
- **穩定度 (Stable %)**: 區分左、右腳，支援 50/70/90/110/free 五種條件。
- **偏移量 (Std Angle)**: 區分左、右腳，支援 50/70/90/110/free 五種條件。

## 🚀 使用說明
1. 修改 `extract_tekfit.py` 中的 `PDF_DIR` 指向你的 PDF 資料夾路徑。
2. 執行腳本：
   ```bash
   python extract_tekfit.py
   ```
3. 完成後於輸出路徑查看 `tekfit_merged.xlsx`。

## ⚠️ 注意事項
- 確保 PDF 檔案頁數至少有 3 頁。
- 檔名需符合格式要求（例如：`條件-ID.pdf`），否則會被跳過。

---
*Developed by Allen @ NTHU-KineMech Lab*
