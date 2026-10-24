@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   ESG 披露核查 · 人工复核台
echo   启动后浏览器打开 http://127.0.0.1:7860
echo   关闭本窗口即停止服务
echo ============================================
".\venv\Scripts\python.exe" "scripts\day5_review_app.py"
pause
