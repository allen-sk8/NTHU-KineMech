@echo off
chcp 65001 >nul 2>&1
echo ==================================================
echo    PASCO 力板垂直跳躍自動化分析系統 - 一鍵全流程
echo ==================================================
echo.

REM 切換至腳本所在目錄 (確保相對路徑正確)
cd /d "%~dp0"

echo [階段一] 轉換原始 .cap 檔案為 CSV 力量數據 ...
echo --------------------------------------------------
python convert_cap_to_csv.py
if %errorlevel% neq 0 (
    echo [錯誤] 階段一轉換失敗！請檢查 Python 環境與 inputs 資料夾。
    pause
    exit /b 1
)
echo.

echo [階段二-A] 分析 CMJ (反向動作蹲跳) 數據 ...
echo --------------------------------------------------
python analyze_cmj.py
if %errorlevel% neq 0 (
    echo [警告] CMJ 分析過程發生錯誤，請檢查輸出日誌。
)
echo.

echo [階段二-B] 分析 SJ (靜態蹲跳) 數據 ...
echo --------------------------------------------------
python analyze_sj.py
if %errorlevel% neq 0 (
    echo [警告] SJ 分析過程發生錯誤，請檢查輸出日誌。
)
echo.

echo ==================================================
echo    全部流程執行完畢！
echo    結果已儲存至 outputs/ 資料夾中。
echo ==================================================
pause
