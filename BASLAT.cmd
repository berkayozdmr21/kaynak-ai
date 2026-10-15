@echo off
cd /d "%~dp0"
title Kaynak AI
echo Kaynak AI baslatiliyor...
where python >nul 2>&1
if errorlevel 1 (
  echo Python bulunamadi. Python 3.10 veya ustunu kurup tekrar deneyin.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo Bos bir port secilecek ve uygulama hazir olunca tarayici acilacak.
echo Siteyi kullanirken bu pencereyi acik tutun.
echo Durdurmak icin Ctrl+C kullanin.
echo.
".venv\Scripts\python.exe" run.py
:failed
echo.
echo Sunucu durdu. Yukaridaki hata mesajini kontrol edin.
pause
