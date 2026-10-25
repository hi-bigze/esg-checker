@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   ESG 披露核查 Agent - Web 应用
echo   启动后浏览器打开 http://127.0.0.1:8000
echo   演示账号 demo / demo1234
echo   关闭本窗口即停止服务
echo ============================================
".\venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
