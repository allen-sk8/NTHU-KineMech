# NTHU-KineMech 實驗室工具集 (Laboratory Tools)

歡迎使用 NTHU-KineMech 實驗室開發的運動科學與生物力學分析工具集。本儲存庫整合了針對棒球表現、步態分析以及 IMU 數據處理的六大核心工具。

## 🛠 工具清單

| 工具名稱 | 資料夾 | 主要功能 | 技術棧 |
| :--- | :--- | :--- | :--- |
| **棒球動作標記工具** | `Baseball_Event_Annotation` | 自動化辨識棒球影片中的關鍵動作點（如出手、接球）。 | YOLOv11, ViTPose |
| **步態分析提取工具** | `Gait_Report_Extractor` | 從 PDF 步態報告中批量提取穩定度與角度數據並整合至 Excel。 | pdfplumber, Python GUI |
| **IMOTEK PDF 讀取器** | `Tekfit_Report_Merger` | 針對 Tekfit 報告進行數據整合，支援多種負重條件分析。 | Python, Pandas |
| **棒球表現綜合分析** | `Baseball_Performance_Analysis` | 結合力板與 Blast 數據，生成球員表現的 3D 診斷地圖。 | Plotly, Scikit-learn |
| **跳躍高度測量工具** | `IMU_Jump_Calculator` | 利用 IMU 感測器數據透過 DTW 演算法計算跳躍高度。 | SciPy, DTW Algorithm |
| **PASCO 力板自動化分析** | `PASCO_Analysis` | 批次將 `.cap` 格式轉換為 CSV 並自動生成跳躍力學指標報表。 | Python, Binary Parsing |

---

## 🚀 快速開始

### 環境需求
- **Python 3.10+** (建議版本)
- 建議為每個工具建立獨立的虛擬環境 (`venv`) 以避免套件衝突。

### 安裝步驟範例
1. 進入特定工具資料夾：
   ```bash
   cd Baseball_Annotation_Tool
   ```
2. 建立虛擬環境：
   ```bash
   python -m venv venv
   ```
3. 啟動虛擬環境：
   - Windows: `.\venv\Scripts\activate`
   - Mac/Linux: `source venv/bin/activate`
4. 安裝依賴：
   ```bash
   pip install -r requirements.txt (或參閱各資料夾內的 README)
   ```

---

## 📂 資料夾說明
各工具的詳細使用說明、輸入資料格式與輸出結果定義，請參閱各子資料夾內的 `README.md`：
- [棒球動作標記工具](./Baseball_Event_Annotation/README.md)
- [步態分析提取工具](./Gait_Report_Extractor/README.md)
- [IMOTEK PDF 讀取器](./Tekfit_Report_Merger/README.md)
- [棒球表現綜合分析](./Baseball_Performance_Analysis/README.md)
- [跳躍高度測量工具](./IMU_Jump_Calculator/README.md)
- [PASCO 力板自動化分析](./PASCO_Analysis/README.md)

---
*Developed by Allen @ NTHU-KineMech Lab*
