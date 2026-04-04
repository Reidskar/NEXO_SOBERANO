@echo off
cd /d C:\Users\Admn\Desktop\NEXO_SOBERANO
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
