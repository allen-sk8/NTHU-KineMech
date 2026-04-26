# Baseball Performance Analysis (棒球表現綜合分析工具)

本工具旨在結合**力板 (Force Plate)** 的爆發力數據與 **Blast Motion** 的揮棒動作數據，構建球員表現的專業診斷地圖。透過統計建模，我們可以量化體能（肌肉發力）轉化為技術（揮棒速度）的效能。

## 🔬 分析邏輯：轉化效能 (Transfer Efficiency)
我們關注以下三個維度的關聯性：
1. **CMJ 推蹬發力率 (RFD)**: 代表神經徵召速度與發力協調性（X軸）。
2. **SJ 跳躍高度**: 代表肌肉的絕對肌力基礎（Y軸）。
3. **揮棒速度 (Swing Speed)**: 最終的技術輸出成果（Z軸）。

工具會自動將上述數據進行配對，並生成 3D 模型以找出表現優異的球員群體特徵。

## 📂 資料夾結構
- `force_plate/`: 存放 CSV 格式的力板數據（區分為 CMJ 與 SJ 資料夾）。
- `blast/`: 存放 Blast Motion 匯出的揮棒數據 CSV。
- `output/`: **[輸出]** 包含生成的互動式 HTML 報表與 Excel 彙總資料。
- `utils/`: 數據處理與視覺化的核心模組。

## 🚀 使用說明
1. 將對應的數據放入 `force_plate` 與 `blast` 資料夾。
2. 開啟 `main_analysis.py` 並修改 `BASE_DIR` 為你的本地路徑。
3. 執行分析：
   ```bash
   python main_analysis.py
   ```
4. 查看 `output/performance_RFD_SJ_Swing.html` 獲得互動式 3D 診斷圖。

## 🎨 輸出亮點
- **互動式 3D 報告**: 可在瀏覽器中旋轉、縮放，並根據球員 ID 進行篩選。
- **統計建模**: 自動計算線性回歸平面，標示出高於或低於預期表現的球員。

---
*Developed by Allen @ NTHU-KineMech Lab*
