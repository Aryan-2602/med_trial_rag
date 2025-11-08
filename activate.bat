@echo off
REM Quick activation script for Windows

call .venv\Scripts\activate.bat
echo Virtual environment activated!
python --version
echo.
echo To deactivate, run: deactivate

