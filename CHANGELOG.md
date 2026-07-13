# Changelog

本專案的所有重大變更都將記錄在此檔案中。

## [Unreleased] - 2026-07-13

### Added
- **分離儲存力量與功率 (Power) 關係圖**: 為了讓運科報表更加簡明，在單一跳躍分析完成後，系統除了原本的對照組 comparison.png 外，亦會自動在背景獨立繪製出「力量-時間關係圖 (Force-Time)」與「功率-時間關係圖 (Power-Time)」兩張精簡圖檔，去除了下半部的時間軸 Timeline 標記。
- **1:1 Flex 報表雙圖並排展示**: 更新 HTML 報表模板，不再使用 CSS 截斷 comparison.png。改用 Flex 左右並排，以 1:1 的黃金比例展示乾淨的力量與功率曲線，版面更顯精緻與專業。
- **Web 伺服器動態 PNG 路由**: 在 `ReportHTTPHandler` 的 `do_GET` 請求中加入 `.png` 動態解析規則，修復了因為 Web 伺服器先前無此路由導致網頁報表上圖片顯示破圖的缺陷，現在網頁端亦能完美顯示最新的力量與功率圖。

### Changed
- **繪圖對象更正**: 依據使用者指正，將先前錯誤的「位移 (Displacement)」曲線圖修正為對運動科學而言更為核心的「功率 (Power)」曲線圖，讓檢測指標更貼合實驗室需求。
- **功率圖 Y 軸零線置中對稱**: 動態計算功率曲線的最大絕對值，將 Y 軸範圍限制在對稱區間，確保 0 刻度線（零功率線）始終在圖表正中央，提升物理學視覺對稱性。

### Changed
- **高質感報表排版美化**:
  - 表格配色方案改為高雅的深靛藍（`#1e3d59`）與淡灰藍（`#f1f5f9`）。
  - 修復左下角「評估指標、衝量、動作時間」欄位名發白、字體過小看不清的設計缺陷。
  - 基本資料表第一欄加入淡灰表單背景，增加排版立體感。
  - 移除表格所有寫死的 inline height，加大單元格 padding 至 `8px 6px` 避免文字被迫直排。

### Fixed
- **多執行緒死鎖 (Deadlock)**: 將 `MonitorState` 的 `Lock` 升級為 `RLock` (可重入鎖)，解決了 `update_result` 內部呼叫 `add_log` 時，同一執行緒自我死結的隱蔽 Bug。
- **Matplotlib 背景繪圖衝突**: 強制使用非交互式後端 `matplotlib.use('Agg')`，徹底消除了 Watchdog 背景線程與 Qt GUI 衝突所導致的 `QObject::~QObject: Timers cannot be stopped from another thread` 與 `forrtl: error (200)` 系統崩潰。
- **瀏覽器彈窗阻塞**: 將 `webbrowser.open` 封裝於獨立的背景守護執行緒 (`daemon Thread`) 中異步啟動，避免 Windows 喚醒預設瀏覽器時對監控主線程的同步阻塞。
- **Windows 中文路徑亂碼與 OSError**: 移除 `subprocess.run` 中所有的 `shell=True` 參數，促使 Windows 直接使用 Unicode API 傳遞中文路徑，徹底解決中文目錄（如 `自動報表測試`）被 Edge 截斷無法生成 PDF 的問題。
- **多跳躍 (Multi-Jump) 平均計算防呆**: 實作 Trial 欄位平均計算時，自動略過非數值欄位（如立板測不到的性別、身高、年齡等個人資訊），確保未填寫個人資料時依然能順利完成平均與分析。
