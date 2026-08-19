@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo             CONVERTER BUILD
echo ============================================
echo.

set "TESS_DIR=C:\Program Files\Tesseract-OCR"

rem Windows App Execution Alias (py/python) can point at an empty environment.
rem Prefer the per-user Python installation, then verify that it has PySide6.
set "PYTHON_CMD=%LocalAppData%\Python\bin\python.exe"
if not exist "%PYTHON_CMD%" set "PYTHON_CMD=python"

"%PYTHON_CMD%" -c "import PySide6, PyInstaller" >nul 2>nul
if errorlevel 1 (
    echo HATA: PySide6 ve PyInstaller bulunan Python ortami bulunamadi.
    echo Beklenen yol: %LocalAppData%\Python\bin\python.exe
    echo Bu ortamda su komutu calistirin:
    echo "%PYTHON_CMD%" -m pip install -r requirements.txt pyinstaller
    pause
    exit /b 1
)

if not exist "main.py" (
    echo HATA: main.py bulunamadi.
    pause
    exit /b 1
)

if not exist "converter-new.ico" (
    echo HATA: converter-new.ico bulunamadi.
    pause
    exit /b 1
)

if not exist "azra-logo.png" (
    echo HATA: azra-logo.png bulunamadi.
    pause
    exit /b 1
)

if not exist "bayrak.jpeg" (
    echo HATA: bayrak.jpeg bulunamadi.
    pause
    exit /b 1
)

if not exist "%TESS_DIR%\tesseract.exe" (
    echo HATA: Tesseract bulunamadi:
    echo %TESS_DIR%\tesseract.exe
    pause
    exit /b 1
)

echo.
echo Eski build temizleniyor...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "ConverteR.spec" del /q "ConverteR.spec"

echo.
echo PREMIUM EXE klasoru olusturuluyor...
"%PYTHON_CMD%" -m PyInstaller --noconfirm --clean --onedir --windowed ^
 --name "ConverteR" ^
 --icon "converter-new.ico" ^
 --add-data "converter-new.ico;." ^
 --add-data "azra-logo.png;." ^
 --add-data "bayrak.jpeg;." ^
 --add-data "rafine-logo.jpg;." ^
 --add-data "emir-logo.jpg;." ^
 --add-data "emir-video.mp4;." ^
 --add-data "emir-yıldız.png;." ^
 --add-data "update_config.json;." ^
 --add-data "%TESS_DIR%;tesseract" ^
 main.py

if errorlevel 1 (
    echo.
    echo HATA: EXE olusturulamadi.
    pause
    exit /b 1
)

if not exist "dist\ConverteR\_internal\PySide6\Qt6Core.dll" (
    echo.
    echo HATA: Qt runtime dosyalari pakete eklenemedi.
    echo Kurulum olusturmayin; Python ortamini ve PySide6 kurulumunu kontrol edin.
    pause
    exit /b 1
)

echo.
echo ============================================
echo BASARILI!
echo Program: dist\ConverteR\ConverteR.exe
echo ICO:     dist\ConverteR\converter-new.ico
echo ============================================
echo.
pause
