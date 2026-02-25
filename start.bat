@echo off
chcp 65001 >nul
echo ============================================
echo  Speech Service (TTS + STT)
echo  API: http://localhost:8080
echo  Frontend: frontend/index.html
echo ============================================
set HF_HUB_CACHE=%~dp0checkpoints\hf_cache
cd /d "%~dp0backend"
uv run --python 3.11 uvicorn speech_service.main:app --host 0.0.0.0 --port 8080
pause
