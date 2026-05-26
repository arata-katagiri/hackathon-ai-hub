@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" cv\inference_loop.py
pause
