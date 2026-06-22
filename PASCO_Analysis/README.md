# PASCO 力板垂直跳躍自動化分析系統 (PASCO Jump Auto-Analyzer)

本系統是一套專為運動科學與臨床生物力學設計的自動化分析工具，旨在將 PASCO 力板產生的專有格式 `.cap` 檔案批次轉換為 CSV 力量數據，並進行高精度的質心運動學積分與臨床進階指標計算，最終自動導出符合實驗室金標準的雙工作表（Details + CMJ）Excel 臨床診斷報告與高質感物理圖表。

---

## 📂 專案目錄結構

本系統採用「**專案子資料夾分類**」與「**單受試者大混合儲存**」之設計，輸入與輸出層級保持高度對稱，所有產出皆一目了然：

```text
PASCO_Analysis/
│
├── inputs/                       # 【原始輸入區】
│   ├── cmj/                      # 存放 CMJ (蹲跳) 專案資料夾
│   │   └── 2026跆拳/             # 👈 範例：實驗室自定義的專案名稱
│   │       ├── 001.cap           # 👈 受試者原始力板檔案
│   │       ├── 002.cap
│   │       └── ...
│   └── sj/                       # 存放 SJ (無蹲跳) 專案資料夾 (預留)
│
├── outputs/                      # 【分析輸出區】
│   ├── cmj/                      # CMJ 動作輸出目錄
│   │   └── 2026跆拳/             # 自動繼承輸入端的專案名稱
│   │       ├── 001/               # 👈 每個 .cap 檔案專屬的獨立資料夾
│   │       │   ├── 001.csv        # [階段一] 轉換出的原始力量 CSV (雙力板合併)
│   │       │   ├── 001-1.xlsx     # [階段二] Run 1 雙 Sheet 臨床報告
│   │       │   ├── 001-2.xlsx     # [階段二] Run 2 雙 Sheet 臨床報告
│   │       │   ├── 001-3.xlsx     # [階段二] Run 3 雙 Sheet 臨床報告
│   │       │   ├── 001-1_comparison.png # [階段二] Run 1 物理診斷圖
│   │       │   ├── 001-2_comparison.png # [階段二] Run 2 物理診斷圖
│   │       │   └── 001-3_comparison.png # [階段二] Run 3 物理診斷圖
│   │       └── 002/
│   │           └── ...
│   └── sj/                       # SJ 動作輸出目錄 (預留)
│
├── convert_cap_to_csv.py         # 核心轉換程式 (階段一：.cap 轉 CSV)
├── analyze_cmj.py                # CMJ 分析主程式 (階段二：CSV 轉 臨床報告與圖表)
├── analyze_sj.py                 # SJ 分析主程式 (預留，未來開發使用)
├── metrics_calculator.py         # 獨立模組：臨床進階指標公式與 Excel 自動格式化
└── requirements.txt              # 專案依賴套件清單
```

---

## 🚀 兩階段操作流程說明

本系統之執行分為兩階段，流程設計簡單且具高度防呆性。請開啟終端機（Terminal）並確保處於專案根目錄下：

### 階段一：解析原始數據 (.cap ➡️ CSV)

將您要分析的力板原始檔案放入對應動作專案目錄中，例如將 `.cap` 檔案置於 `inputs/cmj/2026跆拳/` 下。

執行以下指令進行批次轉換：
```bash
python convert_cap_to_csv.py
```
*   **運作邏輯**：程式將會自動巡覽 `inputs/cmj/` 與 `inputs/sj/` 底下的所有專案資料夾。
*   **輸出結果**：在 `outputs/cmj/專案名稱/受試者ID/` 目錄下自動建立專屬資料夾，並輸出雙力板合併後的 `<受試者ID>.csv` 力量序列檔案。

---

### 階段二：臨床肌力指標分析 (CSV ➡️ 雙 Sheet Excel & 診斷圖)

此階段將針對已轉換的 CSV 進行主要物理運動學與進階肌力指標計算。

對於 CMJ (蹲跳) 動作，執行以下指令：
```bash
python analyze_cmj.py --plot
```
*   **`--plot` 參數**：強烈建議攜帶此參數。啟用後程式會自動為每次跳躍生成高質感的物理診斷圖，方便研究人員直觀檢查特徵點是否定位準確。
*   **輸出結果**：將會在與該受試者 CSV 相同的資料夾下，直接生成以下檔案：
    *   **雙工作表 Excel (`<受試者>-<Run>.xlsx`)**：
        *   `Details` 工作表：包含 11 個特徵事件（動作開始、最大失重、重心最低、離地瞬間等）的精確時間戳、力量值、二次積分位移、速度與功率值。
        *   `CMJ` 工作表：包含實驗室金標準的 20 項肌力特徵（包含衝量、反應力指數 RSI、向心/離心做功量與功率峰值、下蹲/制動/推蹬發力率、以及標準化後的下肢勁度與百分比時間戳等），並自動使用 Excel 大標題合併儲存格格式化。
    *   **物理診斷圖 (`<受試者>-<Run>_comparison.png`)**：展示該次跳躍的原始力、濾波力、位移、速度與功率的等比縮放曲線，並將防呆搜尋窗口（體重區間、SoM 搜尋區間、攤還期）以及 11 個特徵事件點標記出來。

---

## 🛠️ 演算法引數與參數微調

為了應對不同噪聲等級的資料，`analyze_cmj.py` 提供了靈活的參數微調開關。您可以在執行時於終端機直接傳入參數，例如：

```bash
# 修改 Butterworth 濾波切斷頻率為 25.0 Hz，並將 SoM 門檻調低至體重的 2.0%
python analyze_cmj.py --plot --cutoff 25.0 --som-pct 0.02
```

### 可用參數一覽表：

| 參數 | 預設值 | 說明 |
| :--- | :---: | :--- |
| `--plot` | 開啟 | 是否自動生成診斷對比圖 (.png) |
| `--fs` | `1000` | 力板數據的取樣頻率 (Hz) |
| `--cutoff` | `20.0` | Butterworth 低通濾波切斷頻率 (Hz) |
| `--som-pct` | `0.025` | 判定動作開始 (SoM) 時，淨力偏離靜態體重的百分比 (2.5%) |
| `--som-window` | `250` | 從最大失重處往回搜尋 SoM 的最大時間窗口 (ms) |
| `--takeoff-n` | `10.0` | 判定離地瞬間 (Takeoff) 的精確力量閾值 (N) |
| `--landing-n` | `30.0` | 判定著地瞬間 (Landing) 的精確力量閾值 (N) |
| `--landing-window`| `150` | 著地瞬間防餘震干擾之安全屏蔽窗口 (ms) |
| `--amort-before` | `45` | 攤還期起點相對於重心最低點的前推時間偏移 (ms) |
| `--amort-after` | `45` | 攤還期終點相對於重心最低點的後推時間偏移 (ms) |

---

## 📖 指標公式與學術說明手冊

為了方便交接與學術傳承，專案輸出目錄下特別包含了一份 [jump_metrics_documentation.xlsx](file:///c:/Users/allensk8/vscode-all-in-one/Local_workspace/NTHU-KineMech/PASCO_Analysis/outputs/jump_metrics_documentation.xlsx) 說明書。

*   **格式對齊**：該 Excel 文件在排版、合併儲存格上與實驗室報告完全一致。
*   **內容設計**：
    *   在 `Details` 中詳細列出所有特徵事件在程式中的**定位搜尋演算法**與實測 Frame 的 MAE 誤差與相關係數 $r$。
    *   在 `CMJ` 中以「原始」行與「%標準化」行，完整標明了 20 項進階指標的**詳細物理計算公式、標準化方法**，以及在實驗室 61 個控制組乾淨樣本上的**批量信效度誤差統計**。

---

## 🧑‍💻 未來 SJ (Squat Jump) 擴充指引

SJ 的核心執行流程與 CSV 大混合儲存的目錄結構已在專案中配置完畢。
未來若需補上 SJ 的發力率與跳躍分析邏輯：
1. 請參考 [metrics_calculator.py](file:///c:/Users/allensk8/vscode-all-in-one/Local_workspace/NTHU-KineMech/PASCO_Analysis/metrics_calculator.py) 中 `calculate_advanced_metrics` 實作 SJ 專屬的物理特徵（SJ 沒有下蹲與煞車，主要為推進與推蹬發力率）。
2. 在 [analyze_sj.py](file:///c:/Users/allensk8/vscode-all-in-one/Local_workspace/NTHU-KineMech/PASCO_Analysis/analyze_sj.py) 中擴充 SJ 的特徵點定位演算法（SoM 定位可直接尋找力量突破體重 BW 之幀，無須使用 CMJ 的 retrograde 窗口搜尋）。
3. 將產生的 Details 與 SJ 工作表儲存至 `outputs/sj/專案名稱/受試者ID/` 下即可。
