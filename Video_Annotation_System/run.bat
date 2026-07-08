@echo off
chcp 65001 > nul
echo =========================================
echo  影片關鍵幀標註系統啟動程序
echo =========================================
echo.
echo [1/2] 安裝/確認必備套件...
pip install -r requirements.txt

echo.
echo [2/2] 啟動伺服器...
echo 伺服器啟動後，瀏覽器將自動開啟 http://localhost:8000
echo 請勿關閉此視窗！(如需關閉伺服器請按 Ctrl+C)
echo.

start http://localhost:8000
uvicorn main:app --reload --host 0.0.0.0 --port 8000
