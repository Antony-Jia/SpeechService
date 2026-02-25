@echo off
chcp 65001 >nul
echo ============================================
echo  Speech Service (TTS + STT)
echo  API: http://localhost:8080
echo  前端测试页: frontend/index.html
echo ============================================
cd /d "%~dp0backend"
uv run uvicorn speech_service.main:app --host 0.0.0.0 --port 8080
pause
