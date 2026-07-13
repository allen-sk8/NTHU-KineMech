@echo off
chcp 65001 > nul
title PASCO 力板即時監控與自動分析系統
echo --------------------------------------------------
echo        PASCO 力板即時監控與自動分析系統
echo --------------------------------------------------
echo 正在檢查與啟動背景監控服務...
echo.
python realtime_monitor.py
if %errorlevel% neq 0 (
    echo.
    echo 執行過程中發生錯誤，請確認 Python 環境與依賴套件是否正確。
    pause
)
