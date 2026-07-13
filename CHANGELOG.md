# Changelog

本專案的所有重大變更都將記錄在此檔案中。

## [Unreleased] - 2026-07-13

### Added
- **雙重強固時間戳記輪詢**: 網頁前端狀態與報表端 Ajax 重整機制升級為基於 `update_time` 差異對比的強固輪詢，保證多個標籤分頁或快取存在時，皆能 100% 同步重整。
- **跳躍力圖 CSS 裁剪與放大**: 在報表 HTML/PDF 中，使用 CSS `overflow: hidden` 與絕對定位，將跳躍力圖下半部的時間軸隱藏，僅保留上半部的力學曲線，且將圖片寬度撐滿容器放大顯示（而不變更硬碟中儲存的原始完整圖檔）。

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
