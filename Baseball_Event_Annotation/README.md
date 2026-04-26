# Baseball Annotation Tool (棒球動作分析工具)

本工具旨在利用深度學習技術（Object Detection & Pose Estimation）自動化分析棒球影片，辨識關鍵動作時間點（Events）並提取球員骨架資訊。

### 核心技術
- **目標檢測**: 使用 `YOLOv11` 辨識球場上的關鍵物件。
- **姿勢估計**: 整合 `ViTPose` 提取高精度的 2D 人體骨架座標。
- **動作邏輯**: 透過座標軌跡與時間序列分析，自動標記出手（Release）、接球（Catch）等關鍵格。

---

## 📂 資料夾結構說明
- `data/raw/`: **[輸入]** 放置待分析的原始影片檔（.MTS, .mp4）。
- `data/outputs/`: **[輸出]** 分析結果，包含 Excel 匯總表與各影片的詳細座標資料。
- `ultralytics_yolo/`: YOLO 偵測與分析的核心邏輯。
- `vitpose/`: 姿勢估計相關模型配置。
- `ui/`: 工具介面組件。

---
## 步驟一：安裝 Python
如果你尚未安裝 Python，或是版本不對，請依照以下步驟安裝：

1. 前往 Python 官方網站下載 **Python 3.10** 的安裝檔：
   👉 [按這裡下載 Python 3.10 (Windows 64-bit)](https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe)
2. **⚠️ 非常重要**：打開安裝檔後，在第一個畫面底下，請**務必勾選** `Add python.exe to PATH`（將 Python 加入環境變數）。
3. 點擊 `Install Now` 一路按確定直到安裝完成。

---

## 步驟二：開啟終端機與進入資料夾

1. 在你的電腦上找到 `Baseball_Annotation_Tool` 這個資料夾，將你的棒球影片（例如 `.MTS`, `.mp4`）放進 `data/raw/` 資料夾內。
2. 進入 `Baseball_Annotation_Tool` 資料夾後，在視窗上方的「路徑列」點一下，輸入 `powershell` 然後按下 `Enter` 鍵。這會為你開啟一個黑底藍字的 PowerShell 終端機視窗。

---

## 步驟三：建立與啟動虛擬環境 (Virtual Environment)
為了不弄亂你電腦的其他設定，我們要在這個資料夾內建立一個專屬的「虛擬環境」。

在剛剛開啟的 PowerShell 視窗中，**依序複製貼上**並執行以下指令（每貼一行就按一次 Enter）：

1. **允許執行腳本**（如果你沒設定過，系統預設會阻擋後續的啟動動作）：
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
   *(如果出現提示問你要不要更改，請輸入 `Y` 然後按 Enter)*

2. **建立虛擬環境**（這會在資料夾內產生一個名為 `venv` 的資料夾）：
   ```powershell
   python -m venv venv
   ```
   *(這步大約需要等幾秒鐘，等它跑完)*

3. **啟動虛擬環境**：
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
   *(成功的話，你會在指令列的最左邊看到 `(venv)` 的字樣，代表你已經在這個安全環境裡面了！)*

---

## 步驟四：安裝必備套件

在看到最左邊有 `(venv)` 的情況下，複製貼上以下指令來下載並安裝所需的人工智慧與影像處理套件：

```powershell
pip install torch torchvision torchaudio ultralytics opencv-python matplotlib
```

*(這個步驟會下載比較多東西，請耐心等待它跑到 100% 並且結束跳回出入指令的狀態。)*

---

## 步驟五：執行程式開始分析！

安裝完成後，你就可以讓程式去分析 `data/raw/` 資料夾裡面的所有影片了！

請複製貼上以下指令（這行指令會先告訴系統程式碼在哪裡，然後開始執行批次處理）：

```powershell
$env:PYTHONPATH="."; python ultralytics_yolo/pipeline.py --run_all --raw_dir "data/raw"
```

### 🎉 執行成功後去哪裡看結果？
當畫面顯示 `[pipeline] 完成。` 之後，你可以到 `data/outputs/` 資料夾底下尋找：
- `all_events.csv`：裡面記錄了所有影片的動作時間點（接球、腳步、出手等資訊的試算表）。
- 以影片名稱命名的資料夾（例如 `00372_result/`）：裡面儲存了每一偵的骨架座標資料等分析數據。

---

## 常見問題 (FAQ)

**Q1：我下次要再跑一次程式，還需要重新安裝嗎？**
**不需要喔！** 你只需完成 **步驟二** (開啟 powershell) 與 **步驟三的第 3 小步** (啟動虛擬環境：`.\venv\Scripts\Activate.ps1`)。看到出現 `(venv)` 後，直接執行 **步驟五** 的指令即可。

**Q2：如果我只想跑一支影片，而不是整個資料夾？**
請將步驟五的指令替換成這樣，並把最後的檔名改成你的影片名稱：
```powershell
$env:PYTHONPATH="."; python ultralytics_yolo/pipeline.py --video "data/raw/你的影片名稱.MTS"
```
